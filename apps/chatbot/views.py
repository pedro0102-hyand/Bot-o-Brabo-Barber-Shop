import json
import logging
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rag.graph import get_grafo
from apps.chatbot.models import Cliente, Conversa

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def chat(request):
    try:
        body = json.loads(request.body)
        mensagem = body.get("mensagem", "").strip()
        telegram_id = body.get("telegram_id", "rest_user").strip()
        nome = body.get("nome", "Usuário REST").strip()

        if not mensagem:
            return JsonResponse({"erro": "Mensagem vazia."}, status=400)

        # ── 1. Processa no grafo ──────────────────────────────────────────────
        # get_grafo() retorna o singleton compilado — sem recriação a cada request.
        # Executado antes de qualquer escrita no banco: se falhar, nada é persistido.
        grafo = get_grafo()
        resultado = grafo.invoke({
            "mensagem": mensagem,
            "intencao": "",
            "resposta": "",
            "telegram_id": telegram_id,
            "nome_cliente": nome,
        })

        resposta = resultado["resposta"]
        intencao = resultado["intencao"]

        # ── 2. Persiste cliente + conversa na mesma transação ─────────────────
        # transaction.atomic() garante que cliente e conversa são criados
        # juntos — se Conversa.create() falhar, o get_or_create do cliente
        # também é revertido, mantendo o banco consistente.
        with transaction.atomic():
            cliente, _ = Cliente.objects.get_or_create(
                telegram_id=telegram_id,
                defaults={"nome": nome},
            )
            Conversa.objects.create(
                cliente=cliente,
                mensagem=mensagem,
                resposta=resposta,
                intencao=intencao,
            )

        return JsonResponse({"resposta": resposta, "intencao": intencao})

    except Exception as e:
        logger.exception("Erro no endpoint de chat")
        return JsonResponse({"erro": str(e)}, status=500)