import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pipeline import criar_chain

print("🔄 Carregando a chain RAG...")
chain = criar_chain()
print("✅ Chain carregada!\n")

perguntas = [
    "Quais dias da semana a barbearia funciona e em quais horários ?",
]

for pergunta in perguntas:
    print(f"👤 Pergunta: {pergunta}")
    resposta = chain.invoke(pergunta)
    print(f"🤖 Resposta: {resposta}")
    print("-" * 50)