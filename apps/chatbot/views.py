import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.chatbot.services import processar_mensagem

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

        resultado = processar_mensagem(telegram_id, nome, mensagem)
        return JsonResponse(resultado)

    except Exception:
        logger.exception("Erro no endpoint /chat/")
        return JsonResponse({"erro": "Erro interno."}, status=500)