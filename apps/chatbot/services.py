import logging
from django.db import transaction
from rag.graph import get_grafo
from apps.chatbot.models import Cliente, Conversa

logger = logging.getLogger(__name__)


def processar_mensagem(telegram_id: str, nome: str, texto: str) -> dict:
    """
    Executa o grafo e persiste cliente + conversa no banco.

    Retorna dict com 'resposta' e 'intencao'.
    Centraliza a lógica compartilhada entre o endpoint REST e o webhook
    do Telegram — qualquer correção aqui se aplica aos dois ao mesmo tempo.
    """
    grafo = get_grafo()
    resultado = grafo.invoke({
        "mensagem": texto,
        "intencao": "",
        "resposta": "",
        "telegram_id": telegram_id,
        "nome_cliente": nome,
    })

    resposta = resultado["resposta"]
    intencao = resultado["intencao"]

    with transaction.atomic():
        cliente, _ = Cliente.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={"nome": nome},
        )
        Conversa.objects.create(
            cliente=cliente,
            mensagem=texto,
            resposta=resposta,
            intencao=intencao,
        )

    return {"resposta": resposta, "intencao": intencao}