import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.graph import criar_grafo

print("🔄 Carregando o grafo...")
grafo = criar_grafo()
print("✅ Grafo carregado!\n")

testes = [
    "Oi, tudo bem?",
    "Quanto custa o corte de cabelo?",
    "Vocês abrem no domingo?",
    "Quero marcar um horário",
    "Qual o endereço de vocês?",
    "Blablabla xyz",
]

for mensagem in testes:
    print(f"👤 Mensagem: {mensagem}")
    resultado = grafo.invoke({"mensagem": mensagem, "intencao": "", "resposta": ""})
    print(f"🎯 Intenção: {resultado['intencao']}")
    print(f"🤖 Resposta: {resultado['resposta']}")
    print("-" * 50)