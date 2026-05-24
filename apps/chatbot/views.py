import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rag.graph import get_grafo
from apps.chatbot.models import Cliente, Conversa


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

        # get_grafo() retorna o singleton compilado — sem recriação a cada request
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
        return JsonResponse({"erro": str(e)}, status=500)