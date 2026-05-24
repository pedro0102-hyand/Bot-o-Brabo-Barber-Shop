from datetime import datetime, timedelta, date, time
from django.db import transaction, IntegrityError
from .models import Agendamento, Cliente, EstadoAgendamento


def _para_date(valor) -> date:
    """
    Normaliza qualquer representação de data para datetime.date.

    O campo estado["dia"] é serializado como str no JSONField ("2026-05-25"),
    mas parsear_data() retorna um objeto date. Centralizar a conversão aqui
    garante que horarios_livres() e os filter() do banco recebam sempre
    o tipo correto, independente de qual etapa do fluxo está chamando.
    """
    if isinstance(valor, date):
        return valor
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _para_time(valor) -> time:
    """
    Normaliza o retorno de TimeField para datetime.time.

    SQLite via alguns drivers pode retornar o horário como string
    ("09:00:00") em vez de datetime.time. Usar .strftime() direto
    numa string causa AttributeError silencioso em produção.
    """
    if isinstance(valor, time):
        return valor
    # Aceita "HH:MM" e "HH:MM:SS"
    fmt = "%H:%M:%S" if valor.count(":") == 2 else "%H:%M"
    return datetime.strptime(valor, fmt).time()

HORARIOS_DISPONIVEIS = [
    "09:00", "10:00", "11:00", "12:00",
    "14:00", "15:00", "16:00", "17:00", "18:00",
]

SERVICOS = {
    "corte": "corte",
    "cabelo": "corte",
    "barba": "barba",
    "corte e barba": "corte_barba",
    "corte + barba": "corte_barba",
    "hidratacao": "hidratacao",
    "hidratação": "hidratacao",
    "sobrancelha": "sobrancelha",
}


def get_estado(telegram_id):
    try:
        obj = EstadoAgendamento.objects.get(telegram_id=str(telegram_id))
        return obj.dados
    except EstadoAgendamento.DoesNotExist:
        return {}


def set_estado(telegram_id, dados):
    EstadoAgendamento.objects.update_or_create(
        telegram_id=str(telegram_id),
        defaults={"dados": dados},
    )


def limpar_estado(telegram_id):
    EstadoAgendamento.objects.filter(telegram_id=str(telegram_id)).delete()


def horarios_livres(data) -> list:
    """
    Retorna os horários disponíveis para uma data.

    Aceita tanto datetime.date quanto str ("YYYY-MM-DD") — normaliza
    internamente via _para_date() para garantir o tipo correto no
    filter() e evitar falso-positivo de disponibilidade.
    Os valores de TimeField são normalizados via _para_time() para
    cobrir drivers que retornam string em vez de datetime.time.
    """
    data_normalizada = _para_date(data)

    agendados = Agendamento.objects.filter(
        data=data_normalizada,
        status="confirmado",
    ).values_list("horario", flat=True)

    agendados_str = {_para_time(h).strftime("%H:%M") for h in agendados}
    return [h for h in HORARIOS_DISPONIVEIS if h not in agendados_str]


def parsear_data(texto):
    """Converte texto em data."""
    texto = texto.lower().strip()
    hoje = datetime.now().date()

    if texto in ["hoje"]:
        return hoje
    if texto in ["amanhã", "amanha"]:
        return hoje + timedelta(days=1)

    dias_semana = {
        "segunda": 0, "terça": 1, "terca": 1,
        "quarta": 2, "quinta": 3, "sexta": 4, "sábado": 5, "sabado": 5,
    }

    for nome, num in dias_semana.items():
        if nome in texto:
            dias_ate = (num - hoje.weekday()) % 7
            if dias_ate == 0:
                dias_ate = 7
            return hoje + timedelta(days=dias_ate)

    # Tenta formato DD/MM
    try:
        return datetime.strptime(texto, "%d/%m").replace(year=hoje.year).date()
    except ValueError:
        pass

    # Tenta formato DD/MM/YYYY
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        pass

    return None


def parsear_horario(texto):
    """Converte texto em horário."""
    texto = texto.strip().replace("h", ":00").replace("H", ":00")
    if ":" not in texto:
        texto = texto + ":00"
    try:
        h = datetime.strptime(texto, "%H:%M")
        return h.strftime("%H:%M")
    except ValueError:
        return None


def _voltar_para_horario(telegram_id, estado):
    """
    Regride o estado para aguardando_horario e retorna a mensagem
    com os horários ainda disponíveis. Usado quando o horário
    escolhido é ocupado por outra pessoa durante a confirmação.
    """
    livres = horarios_livres(estado["dia"])

    if not livres:
        # Dia inteiramente lotado — volta uma etapa a mais
        estado_novo = {"etapa": "aguardando_dia"}
        set_estado(telegram_id, estado_novo)
        data_fmt = _para_date(estado["dia"]).strftime("%d/%m/%Y")
        return (
            f"⚠️ O horário que você escolheu acabou de ser reservado por outra pessoa "
            f"e {data_fmt} não tem mais horários disponíveis.\n\n"
            "Por favor, escolha outro dia:\n"
            "Ex: amanhã, segunda, 20/06"
        )

    estado["etapa"] = "aguardando_horario"
    # Remove o horário inválido do estado, mantém o dia
    estado.pop("horario", None)
    estado.pop("servico", None)
    set_estado(telegram_id, estado)

    data_fmt = _para_date(estado["dia"]).strftime("%d/%m/%Y")
    horarios_txt = " · ".join(livres)
    return (
        f"⚠️ O horário que você escolheu acabou de ser reservado por outra pessoa.\n\n"
        f"Horários ainda disponíveis em {data_fmt}:\n"
        f"⏰ {horarios_txt}\n\n"
        "Qual horário prefere?"
    )


def processar_agendamento(telegram_id, texto, nome_cliente):
    """Gerencia o fluxo de agendamento."""
    estado = get_estado(telegram_id)
    etapa = estado.get("etapa", "inicio")

    # ETAPA 1 — Pedir o dia
    if etapa == "inicio":
        set_estado(telegram_id, {"etapa": "aguardando_dia"})
        return (
            "Ótimo! Vamos agendar seu horário. 📅\n"
            "Qual dia você prefere?\n"
            "Ex: hoje, amanhã, segunda, 15/05"
        )

    # ETAPA 2 — Receber o dia, pedir o horário
    if etapa == "aguardando_dia":
        data = parsear_data(texto)
        if not data:
            return "Não entendi o dia. Tente: hoje, amanhã, segunda, ou 15/05 📅"

        livres = horarios_livres(data)
        if not livres:
            return f"Infelizmente não temos horários disponíveis em {data.strftime('%d/%m/%Y')}. Tente outro dia!"

        estado["dia"] = str(data)
        estado["etapa"] = "aguardando_horario"
        set_estado(telegram_id, estado)

        horarios_txt = " · ".join(livres)
        return (
            f"Horários disponíveis em {data.strftime('%d/%m/%Y')}:\n"
            f"⏰ {horarios_txt}\n\n"
            "Qual horário prefere?"
        )

    # ETAPA 3 — Receber o horário, pedir o serviço
    if etapa == "aguardando_horario":
        horario = parsear_horario(texto)
        livres = horarios_livres(estado["dia"])

        if not horario or horario not in livres:
            horarios_txt = " · ".join(livres)
            return f"Horário indisponível. Escolha um desses:\n⏰ {horarios_txt}"

        estado["horario"] = horario
        estado["etapa"] = "aguardando_servico"
        set_estado(telegram_id, estado)

        return (
            "Qual serviço você deseja? ✂️\n\n"
            "1 - Corte de cabelo (R$ 45)\n"
            "2 - Barba (R$ 35)\n"
            "3 - Corte + Barba (R$ 70)\n"
            "4 - Hidratação (R$ 50)\n"
            "5 - Sobrancelha (R$ 25)"
        )

    # ETAPA 4 — Receber o serviço, pedir confirmação
    if etapa == "aguardando_servico":
        texto_lower = texto.lower().strip()

        opcoes_numericas = {
            "1": "corte", "2": "barba", "3": "corte_barba",
            "4": "hidratacao", "5": "sobrancelha",
        }

        servico = opcoes_numericas.get(texto_lower)
        if not servico:
            for chave, valor in SERVICOS.items():
                if chave in texto_lower:
                    servico = valor
                    break

        if not servico:
            return "Não entendi o serviço. Digite 1, 2, 3, 4 ou 5 conforme as opções acima. ✂️"

        estado["servico"] = servico
        estado["etapa"] = "aguardando_confirmacao"
        set_estado(telegram_id, estado)

        nomes_servicos = {
            "corte": "Corte de cabelo",
            "barba": "Barba",
            "corte_barba": "Corte + Barba",
            "hidratacao": "Hidratação",
            "sobrancelha": "Sobrancelha",
        }

        data_fmt = _para_date(estado["dia"]).strftime("%d/%m/%Y")
        return (
            f"Confirma o agendamento? ✅\n\n"
            f"📅 Data: {data_fmt}\n"
            f"⏰ Horário: {estado['horario']}\n"
            f"✂️ Serviço: {nomes_servicos[servico]}\n\n"
            "Responda sim ou não."
        )

    # ETAPA 5 — Confirmar e salvar com proteção contra race condition
    if etapa == "aguardando_confirmacao":
        if texto.lower().strip() in ["sim", "s", "yes", "confirmo", "ok"]:
            try:
                with transaction.atomic():
                    # Trava os registros de agendamento para essa data/horário
                    # enquanto a transação estiver aberta, impedindo inserção dupla.
                    conflito = (
                        Agendamento.objects
                        .select_for_update()
                        .filter(
                            data=_para_date(estado["dia"]),
                            horario=estado["horario"],
                            status="confirmado",
                        )
                        .exists()
                    )

                    if conflito:
                        # Horário foi tomado após a escolha do usuário —
                        # regride o fluxo para que ele escolha outro horário.
                        return _voltar_para_horario(telegram_id, estado)

                    cliente, _ = Cliente.objects.get_or_create(
                        telegram_id=str(telegram_id),
                        defaults={"nome": nome_cliente},
                    )
                    Agendamento.objects.create(
                        cliente=cliente,
                        servico=estado["servico"],
                        data=_para_date(estado["dia"]),
                        horario=estado["horario"],
                        status="confirmado",
                    )

                limpar_estado(telegram_id)
                return (
                    "Agendamento confirmado! 🎉\n"
                    "Te esperamos na Barbearia O Brabo! 💈\n"
                    "Qualquer dúvida é só chamar!"
                )

            except IntegrityError:
                # Salvaguarda: se duas transações passarem pelo select_for_update
                # quase simultaneamente e uma ganhar a corrida, a outra cai aqui.
                return _voltar_para_horario(telegram_id, estado)

        elif texto.lower().strip() in ["não", "nao", "n", "no", "cancelar"]:
            limpar_estado(telegram_id)
            return "Agendamento cancelado. Quando quiser marcar é só falar! 😊"

        else:
            return "Responda sim para confirmar ou não para cancelar."

    limpar_estado(telegram_id)
    return "Algo deu errado. Tente novamente!"