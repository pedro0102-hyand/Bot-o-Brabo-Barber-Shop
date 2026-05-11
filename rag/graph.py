import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from rag.pipeline import criar_chain

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")

# Chain RAG
rag_chain = criar_chain()

# LLM para classificação
llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.7,
)


# Estado da conversa
class Estado(TypedDict):

    mensagem: str
    intencao: str
    resposta: str


# Nó 1 — Classificar intenção
def classificar(estado: Estado) -> Estado:
    mensagem = estado["mensagem"]

    prompt = f"""Classifique a mensagem abaixo em uma dessas categorias:
- saudacao: cumprimentos como oi, olá, bom dia, boa tarde, boa noite, tudo bem
- pergunta: dúvidas sobre preços, serviços, horários, localização, pagamento
- agendamento: quer marcar, agendar, reservar horário
- fallback: qualquer outra coisa que não se encaixa nas anteriores

Responda APENAS com uma palavra: saudacao, pergunta, agendamento ou fallback.

Mensagem: {mensagem}
Categoria:"""

    resposta = llm.invoke([HumanMessage(content=prompt)])
    intencao = resposta.content.strip().lower()

    # Garante que a intenção é válida
    if intencao not in ["saudacao", "pergunta", "agendamento", "fallback"]:
        intencao = "fallback"

    return {"mensagem": mensagem, "intencao": intencao, "resposta": ""}


# Nó 2 — Saudação
def saudacao(estado: Estado) -> Estado:
    resposta = (
        "Olá! Bem-vindo à Barbearia O Brabo! 💈\n"
        "Posso te ajudar com informações sobre nossos serviços, preços, horários e agendamentos.\n"
        "Como posso te ajudar?"
    )
    return {**estado, "resposta": resposta}


# Nó 3 — Pergunta via RAG
def pergunta(estado: Estado) -> Estado:
    resposta = rag_chain.invoke(estado["mensagem"])
    return {**estado, "resposta": resposta}


# Nó 4 — Agendamento (placeholder por enquanto)
def agendamento(estado: Estado) -> Estado:
    resposta = (
        "Para agendar um horário, entre em contato conosco! 📱\n"
        "Em breve você poderá agendar diretamente por aqui. 😉"
    )
    return {**estado, "resposta": resposta}


# Nó 5 — Fallback
def fallback(estado: Estado) -> Estado:
    resposta = (
        "Desculpe, não entendi muito bem. 😅\n"
        "Posso te ajudar com informações sobre preços, serviços, horários ou agendamentos.\n"
        "Pode reformular sua pergunta?"
    )
    return {**estado, "resposta": resposta}


# Roteador
def rotear(estado: Estado) -> Literal["saudacao", "pergunta", "agendamento", "fallback"]:
    return estado["intencao"]


# Construir o grafo
def criar_grafo():
    grafo = StateGraph(Estado)

    grafo.add_node("classificar", classificar)
    grafo.add_node("saudacao", saudacao)
    grafo.add_node("pergunta", pergunta)
    grafo.add_node("agendamento", agendamento)
    grafo.add_node("fallback", fallback)

    grafo.set_entry_point("classificar")

    grafo.add_conditional_edges(
        "classificar",
        rotear,
        {
            "saudacao": "saudacao",
            "pergunta": "pergunta",
            "agendamento": "agendamento",
            "fallback": "fallback",
        }
    )

    grafo.add_edge("saudacao", END)
    grafo.add_edge("pergunta", END)
    grafo.add_edge("agendamento", END)
    grafo.add_edge("fallback", END)

    return grafo.compile()