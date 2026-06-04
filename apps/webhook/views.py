import json
import logging
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.chatbot.services import processar_mensagem

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def enviar_mensagem(chat_id, texto):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": texto})


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return JsonResponse({"ok": True})

    try:
        body = json.loads(request.body)
        mensagem = body.get("message", {})
        chat_id = mensagem.get("chat", {}).get("id")
        texto = mensagem.get("text", "").strip()
        nome = mensagem.get("from", {}).get("first_name", "")

        if not chat_id or not texto:
            return JsonResponse({"ok": True})

        resultado = processar_mensagem(str(chat_id), nome, texto)

        # Fora do processar_mensagem: falha de rede não deve afetar
        # o registro da conversa que já foi salvo com sucesso.
        enviar_mensagem(chat_id, resultado["resposta"])
        return JsonResponse({"ok": True})

    except Exception:
        logger.exception("Erro no webhook do Telegram")
        return JsonResponse({"erro": "Erro interno."}, status=500)

