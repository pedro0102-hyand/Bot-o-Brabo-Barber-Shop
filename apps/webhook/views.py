import json
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rag.graph import criar_grafo
from apps.chatbot.models import Cliente, Conversa

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

grafo = criar_grafo()


def enviar_mensagem(chat_id, texto):
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
            nome = mensagem.get("from", {}).get("first_name", "")

            if not chat_id or not texto:
                return JsonResponse({"ok": True})

            # Salva ou recupera o cliente
            cliente, _ = Cliente.objects.get_or_create(
                telegram_id=str(chat_id),
                defaults={"nome": nome},
            )

            # Processa no grafo
            resultado = grafo.invoke({
                "mensagem": texto,
                "intencao": "",
                "resposta": "",
                "telegram_id": str(chat_id),
                "nome_cliente": nome,
            })

            resposta = resultado["resposta"]
            intencao = resultado["intencao"]

            # Salva a conversa
            Conversa.objects.create(
                cliente=cliente,
                mensagem=texto,
                resposta=resposta,
                intencao=intencao,
            )

            enviar_mensagem(chat_id, resposta)
            return JsonResponse({"ok": True})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)

    return JsonResponse({"ok": True})
