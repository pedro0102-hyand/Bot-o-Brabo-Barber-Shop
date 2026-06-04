import os
import threading
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")

# ── Singleton ────────────────────────────────────────────────────────────────
#
# Problema original: rag_chain e llm eram instanciados no nível do módulo,
# o que significa que ao importar graph.py (no boot do Django) o servidor
# tentava conectar ao Ollama e ao ChromaDB imediatamente. Se o Ollama não
# estivesse rodando, o processo crashava antes de aceitar qualquer requisição.
#
# Além disso, criar_grafo() era chamado em cada requisição, recompilando o
# StateGraph e reinicializando embeddings a cada POST — caro e desnecessário.
#
# Solução: lazy initialization com double-checked locking.
# - _grafo_cache, _rag_chain e _llm começam como None.
# - get_grafo() inicializa tudo na primeira chamada e reutiliza nas demais.
# - O Lock garante que duas threads não inicializem ao mesmo tempo.
# ─────────────────────────────────────────────────────────────────────────────

_grafo_cache = None
_rag_chain = None
_llm = None
_lock = threading.Lock()


def _inicializar():
    """
    Instancia rag_chain, llm e compila o grafo LangGraph.
    Chamado uma única vez, protegido pelo _lock.
    Separado de get_grafo() para facilitar testes unitários
    (basta mockar _inicializar antes da primeira chamada).
    """
    global _grafo_cache, _rag_chain, _llm

    from rag.pipeline import criar_chain

    _rag_chain = criar_chain()          # carrega ChromaDB + embeddings Ollama
    _llm = ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )
    _grafo_cache = _criar_grafo_compilado()


def get_grafo():
    """
    Retorna o grafo compilado, inicializando na primeira chamada (lazy).

    Usa double-checked locking: verifica _grafo_cache sem o lock primeiro
    (caminho rápido para todas as requisições após a primeira), e só adquire
    o lock se o cache estiver vazio (apenas na inicialização).
    """
    global _grafo_cache

    if _grafo_cache is None:                    # verificação rápida sem lock
        with _lock:
            if _grafo_cache is None:            # segunda verificação com lock
                _inicializar()

    return _grafo_cache


# ── Tipagem do estado ────────────────────────────────────────────────────────

class Estado(TypedDict):
    mensagem: str
    intencao: str
    resposta: str
    telegram_id: str
    nome_cliente: str
    agendamento_ativo: bool   # True quando há fluxo de agendamento em andamento


# ── Nós do grafo ─────────────────────────────────────────────────────────────

def _tem_agendamento_ativo(telegram_id: str) -> bool:
    """Retorna True se o usuário tem um fluxo de agendamento em andamento."""
    try:
        from apps.chatbot.agendamento import get_estado
        return bool(get_estado(telegram_id).get("etapa"))
    except Exception:
        return False


def classificar(estado: Estado) -> Estado:
    """
    Classifica a intenção da mensagem.

    Comportamento com agendamento ativo:
    - Perguntas e saudações são tratadas normalmente (RAG / boas-vindas),
      preservando a etapa do agendamento. O nó destino acrescenta um
      lembrete ao final da resposta para o usuário não perder o fio.
    - Mensagens que o LLM classifica como 'agendamento' continuam o fluxo.
    - 'fallback' também continua o fluxo, pois pode ser uma resposta
      válida à pergunta atual da etapa (ex: digitar um horário ou serviço).

    Dessa forma o usuário pode tirar dúvidas no meio do agendamento sem
    precisar cancelar, e ainda recebe o lembrete de onde parou.
    """
    mensagem = estado["mensagem"]
    telegram_id = estado.get("telegram_id", "")

    agendamento_ativo = _tem_agendamento_ativo(telegram_id)

    prompt = f"""Classifique a mensagem abaixo em uma dessas categorias:
- saudacao: cumprimentos como oi, olá, bom dia, boa tarde, boa noite, tudo bem
- pergunta: dúvidas sobre preços, serviços, horários, localização, pagamento
- agendamento: quer marcar, agendar, reservar horário
- fallback: qualquer outra coisa que não se encaixa nas anteriores

Responda APENAS com uma palavra: saudacao, pergunta, agendamento ou fallback.

Mensagem: {mensagem}
Categoria:"""

    resposta = _llm.invoke([HumanMessage(content=prompt)])
    intencao = resposta.content.strip().lower()

    if intencao not in ["saudacao", "pergunta", "agendamento", "fallback"]:
        intencao = "fallback"

    # Com agendamento ativo, apenas perguntas e saudações "escapam" do fluxo.
    # Fallback permanece no fluxo porque costuma ser uma resposta à etapa atual
    # (ex: o usuário digita "09:00" — o LLM classifica como fallback, mas é a
    # resposta esperada pela etapa aguardando_horario).
    if agendamento_ativo and intencao not in ("pergunta", "saudacao"):
        intencao = "agendamento"

    return {**estado, "intencao": intencao, "agendamento_ativo": agendamento_ativo}


def _lembrete_agendamento(telegram_id: str) -> str:
    """
    Retorna uma string com o lembrete da etapa pendente do agendamento,
    para ser acrescentada ao final de respostas de pergunta e saudação.
    """
    try:
        from apps.chatbot.agendamento import get_estado
        etapa = get_estado(telegram_id).get("etapa", "")
    except Exception:
        return ""

    lembretes = {
        "aguardando_dia":          "\n\n📅 Você ainda tem um agendamento em andamento. Qual dia prefere?",
        "aguardando_horario":      "\n\n⏰ Você ainda tem um agendamento em andamento. Qual horário prefere?",
        "aguardando_servico":      "\n\n✂️ Você ainda tem um agendamento em andamento. Qual serviço deseja? (1-5)",
        "aguardando_confirmacao":  "\n\n✅ Você ainda tem um agendamento aguardando confirmação. Responda sim ou não.",
    }
    return lembretes.get(etapa, "")


def saudacao(estado: Estado) -> Estado:
    resposta = (
        "Olá! Bem-vindo à Barbearia O Brabo! 💈\n"
        "Posso te ajudar com informações sobre nossos serviços, preços, horários e agendamentos.\n"
        "Como posso te ajudar?"
    )
    if estado.get("agendamento_ativo"):
        resposta += _lembrete_agendamento(estado["telegram_id"])
    return {**estado, "resposta": resposta}


def pergunta(estado: Estado) -> Estado:
    resposta = _rag_chain.invoke(estado["mensagem"])
    if estado.get("agendamento_ativo"):
        resposta += _lembrete_agendamento(estado["telegram_id"])
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


# ── Compilação do grafo ───────────────────────────────────────────────────────

def _criar_grafo_compilado():
    """
    Monta e compila o StateGraph. Chamado uma única vez por _inicializar().
    Separado de get_grafo() para que a estrutura do grafo permaneça legível
    e testável independentemente do mecanismo de cache.
    """
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


