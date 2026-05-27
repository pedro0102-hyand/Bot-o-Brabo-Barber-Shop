import json
import os
import requests
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rag.graph import get_grafo
from apps.chatbot.models import Cliente, Conversa

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


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

            # ── 1. Processa no grafo ──────────────────────────────────────────
            # Executado ANTES de qualquer escrita no banco.
            # Se o grafo lançar exceção, nenhum registro é criado —
            # evita o cenário anterior onde o cliente era persistido
            # mas a conversa nunca chegava a ser salva.
            grafo = get_grafo()
            resultado = grafo.invoke({
                "mensagem": texto,
                "intencao": "",
                "resposta": "",
                "telegram_id": str(chat_id),
                "nome_cliente": nome,
            })

            resposta = resultado["resposta"]
            intencao = resultado["intencao"]

            # ── 2. Persiste cliente + conversa na mesma transação ─────────────
            # transaction.atomic() garante que cliente e conversa são criados
            # juntos — se Conversa.create() falhar, o get_or_create do cliente
            # também é revertido, mantendo o banco consistente.
            with transaction.atomic():
                cliente, _ = Cliente.objects.get_or_create(
                    telegram_id=str(chat_id),
                    defaults={"nome": nome},
                )
                Conversa.objects.create(
                    cliente=cliente,
                    mensagem=texto,
                    resposta=resposta,
                    intencao=intencao,
                )

            # ── 3. Envia a resposta ao Telegram ──────────────────────────────
            # Fora do atomic: falha de rede não deve reverter o registro
            # da conversa que já foi salva com sucesso.
            enviar_mensagem(chat_id, resposta)
            return JsonResponse({"ok": True})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)

    return JsonResponse({"ok": True})
