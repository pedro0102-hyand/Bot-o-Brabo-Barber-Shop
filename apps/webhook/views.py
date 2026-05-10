import json
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rag.pipeline import criar_chain

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

chain = criar_chain()


def enviar_mensagem(chat_id, texto):
    """Envia mensagem para o usuário no Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
    }
    requests.post(url, json=payload)


@csrf_exempt
def webhook(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            mensagem = body.get("message", {})
            chat_id = mensagem.get("chat", {}).get("id")
            texto = mensagem.get("text", "").strip()

            if not chat_id or not texto:
                return JsonResponse({"ok": True})

            resposta = chain.invoke(texto)
            enviar_mensagem(chat_id, resposta)

            return JsonResponse({"ok": True})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)

    return JsonResponse({"ok": True})
