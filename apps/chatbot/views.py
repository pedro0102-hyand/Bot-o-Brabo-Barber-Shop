import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rag.pipeline import criar_chain

chain = criar_chain()


@csrf_exempt
@require_POST
def chat(request):
    try:
        body = json.loads(request.body)
        mensagem = body.get("mensagem", "").strip()

        if not mensagem:
            return JsonResponse({"erro": "Mensagem vazia."}, status=400)

        resposta = chain.invoke(mensagem)
        return JsonResponse({"resposta": resposta})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)