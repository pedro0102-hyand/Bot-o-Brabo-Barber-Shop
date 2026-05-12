import os
import django
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from rag.pipeline import criar_chain

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")

rag_chain = criar_chain()

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
)


class Estado(TypedDict):
    mensagem: str
    intencao: str
    resposta: str
    telegram_id: str
    nome_cliente: str


def classificar(estado: Estado) -> Estado:
    mensagem = estado["mensagem"]
    telegram_id = estado.get("telegram_id", "")

    # Verifica se já está em fluxo de agendamento
    try:
        from apps.chatbot.agendamento import get_estado
        estado_agendamento = get_estado(telegram_id)
        if estado_agendamento.get("etapa"):
            return {**estado, "intencao": "agendamento"}
    except Exception:
        pass

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

    if intencao not in ["saudacao", "pergunta", "agendamento", "fallback"]:
        intencao = "fallback"

    return {**estado, "intencao": intencao}


def saudacao(estado: Estado) -> Estado:
    resposta = (
        "Olá! Bem-vindo à Barbearia O Brabo! 💈\n"
        "Posso te ajudar com informações sobre nossos serviços, preços, horários e agendamentos.\n"
        "Como posso te ajudar?"
    )
    return {**estado, "resposta": resposta}


def pergunta(estado: Estado) -> Estado:
    resposta = rag_chain.invoke(estado["mensagem"])
    return {**estado, "resposta": resposta}


def agendamento(estado: Estado) -> Estado:
    from apps.chatbot.agendamento import processar_agendamento
    resposta = processar_agendamento(
        estado["telegram_id"],
        estado["mensagem"],
        estado["nome_cliente"],
    )
    return {**estado, "resposta": resposta}


def fallback(estado: Estado) -> Estado:
    resposta = (
        "Desculpe, não entendi muito bem. 😅\n"
        "Posso te ajudar com informações sobre preços, serviços, horários ou agendamentos.\n"
        "Pode reformular sua pergunta?"
    )
    return {**estado, "resposta": resposta}


def rotear(estado: Estado) -> Literal["saudacao", "pergunta", "agendamento", "fallback"]:
    return estado["intencao"]


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