import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/barbearia.txt")
VECTORSTORE_PATH = os.path.join(os.path.dirname(__file__), "../vectorstore")

# Criação do vectorstore e da chain RAG
def criar_vectorstore():
    """Carrega o documento e cria o vectorstore no ChromaDB."""
    loader = TextLoader(DATA_PATH, encoding="utf-8")
    documentos = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(documentos)

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTORSTORE_PATH,
    )

    print(f"✅ Vectorstore criado com {len(chunks)} chunks.")
    return vectorstore


def carregar_vectorstore():
    """Carrega o vectorstore existente."""
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    vectorstore = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=embeddings,
    )

    return vectorstore


def criar_chain():
    """Cria a chain RAG completa."""
    vectorstore = carregar_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
    )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""Você é um assistente virtual da Barbearia O Brabo, localizada em Nova Iguaçu, RJ.
Responda apenas com base nas informações fornecidas abaixo.
Se não souber a resposta, diga educadamente que não possui essa informação.
Responda sempre em português, de forma simpática e objetiva.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
    )

    def formatar_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | formatar_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain