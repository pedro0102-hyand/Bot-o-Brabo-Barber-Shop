from datetime import datetime, timedelta
from .models import Agendamento, Cliente

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

# Estado temporário da conversa em memória
# {telegram_id: {etapa, dia, horario, servico}}
estados = {}


def get_estado(telegram_id):
    return estados.get(str(telegram_id), {})


def set_estado(telegram_id, dados):
    estados[str(telegram_id)] = dados


def limpar_estado(telegram_id):
    estados.pop(str(telegram_id), None)


def horarios_livres(data):
    """Retorna horários disponíveis para uma data."""
    agendados = Agendamento.objects.filter(
        data=data,
        status="confirmado"
    ).values_list("horario", flat=True)

    agendados_str = [h.strftime("%H:%M") for h in agendados]
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
            "5 - Sobrancelha (R$ 20)"
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

        data_fmt = datetime.strptime(estado["dia"], "%Y-%m-%d").strftime("%d/%m/%Y")
        return (
            f"Confirma o agendamento? ✅\n\n"
            f"📅 Data: {data_fmt}\n"
            f"⏰ Horário: {estado['horario']}\n"
            f"✂️ Serviço: {nomes_servicos[servico]}\n\n"
            "Responda sim ou não."
        )

    # ETAPA 5 — Confirmar e salvar
    if etapa == "aguardando_confirmacao":
        if texto.lower().strip() in ["sim", "s", "yes", "confirmo", "ok"]:
            try:
                cliente, _ = Cliente.objects.get_or_create(
                    telegram_id=str(telegram_id),
                    defaults={"nome": nome_cliente},
                )
                Agendamento.objects.create(
                    cliente=cliente,
                    servico=estado["servico"],
                    data=estado["dia"],
                    horario=estado["horario"],
                    status="confirmado",
                )
                limpar_estado(telegram_id)
                return (
                    "Agendamento confirmado! 🎉\n"
                    "Te esperamos na Barbearia O Brabo! 💈\n"
                    "Qualquer dúvida é só chamar!"
                )
            except Exception:
                limpar_estado(telegram_id)
                return "Esse horário acabou de ser reservado. Por favor, escolha outro horário!"

        elif texto.lower().strip() in ["não", "nao", "n", "no", "cancelar"]:
            limpar_estado(telegram_id)
            return "Agendamento cancelado. Quando quiser marcar é só falar! 😊"

        else:
            return "Responda sim para confirmar ou não para cancelar."

    limpar_estado(telegram_id)
    return "Algo deu errado. Tente novamente!"