# 💈 Barber Shop Bot — Barbearia O Brabo

Chatbot inteligente para a **Barbearia O Brabo** (Nova Iguaçu, RJ) integrado ao Telegram, com RAG, LLM local e agendamento automatizado.

---

## 🎯 Funcionalidades

- 💬 Responde perguntas sobre preços, serviços, horários, localização e formas de pagamento
- 📅 Realiza agendamentos completos via conversa no Telegram
- 🧠 Usa RAG (Retrieval-Augmented Generation) para responder apenas com dados reais
- 🔄 Detecta automaticamente a intenção de cada mensagem (saudação, pergunta, agendamento, fallback)
- 💾 Salva clientes, conversas e agendamentos no banco de dados
- 🖥️ Painel admin para visualizar tudo

---

## 🏗️ Arquitetura

```
Usuário
   ↓
Telegram
   ↓
Webhook Django
   ↓
LangGraph (roteador de intenções)
   ├── Saudação
   ├── Pergunta → RAG (LangChain + ChromaDB + Ollama)
   ├── Agendamento → Fluxo conversacional + SQLite
   └── Fallback
```

---

## 🛠️ Stack

| Tecnologia | Responsabilidade |
|---|---|
| Django 5.2 | Backend, webhooks, banco de dados |
| LangChain | Pipeline RAG |
| LangGraph | Fluxos conversacionais |
| ChromaDB | Banco vetorial |
| Ollama + gemma2:2b | LLM local para geração de respostas |
| nomic-embed-text | Embeddings locais |
| Telegram Bot API | Interface de chat |
| ngrok | Túnel para desenvolvimento local |

---

## 📁 Estrutura do Projeto

```
Barber Shop Bot/
│
├── apps/
│   ├── chatbot/
│   │   ├── models.py        # Cliente, Conversa, Agendamento
│   │   ├── views.py         # Endpoint REST /api/chatbot/chat/
│   │   ├── admin.py         # Painel admin
│   │   ├── agendamento.py   # Fluxo de agendamento
│   │   └── urls.py
│   │
│   └── webhook/
│       ├── views.py         # Webhook do Telegram
│       └── urls.py
│
├── core/
│   ├── settings.py
│   └── urls.py
│
├── rag/
│   ├── pipeline.py          # Pipeline RAG (ingestão e consulta)
│   ├── graph.py             # Grafo LangGraph
│   ├── ingest.py            # Script de ingestão dos dados
│   ├── test_rag.py          # Testes do RAG
│   └── test_graph.py        # Testes do grafo
│
├── data/
│   └── barbearia.txt        # Base de conhecimento
│
├── vectorstore/             # ChromaDB (gerado automaticamente)
├── docs/
├── venv/
├── .env                     # Variáveis de ambiente (não subir no git)
├── .gitignore
├── requirements.txt
├── manage.py

```

---

## ⚙️ Pré-requisitos

- Python 3.12+
- [Ollama](https://ollama.com) instalado e rodando
- Modelos Ollama baixados:
  ```bash
  ollama pull gemma2:2b
  ollama pull nomic-embed-text
  ```
- [ngrok](https://ngrok.com) instalado e configurado
- Bot criado no Telegram via [@BotFather](https://t.me/BotFather)

---

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/barber-shop-bot.git
cd barber-shop-bot
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gemma2:2b
EMBEDDING_MODEL=nomic-embed-text

# Telegram
TELEGRAM_BOT_TOKEN=seu-token-aqui
```

Para gerar a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 5. Execute as migrations

```bash
python manage.py migrate
```

### 6. Crie o superusuário (admin)

```bash
python manage.py createsuperuser
```

### 7. Indexe a base de conhecimento

```bash
python rag/ingest.py
```

---

## 🧪 Testes

Testar o RAG isoladamente:
```bash
python rag/test_rag.py
```

Testar o grafo LangGraph:
```bash
python rag/test_graph.py
```

Testar o endpoint REST:
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Quanto custa o corte de cabelo?"}'
```

---

## 🧠 Como funciona o RAG

```
Ingestão (uma vez):
barbearia.txt → chunks (500 chars) → embeddings (nomic-embed-text) → ChromaDB

Consulta (cada pergunta):
Pergunta → embedding → busca por similaridade (cosine) → top-3 chunks → prompt → gemma2:2b → resposta
```

O sistema responde **apenas com dados reais** da base de conhecimento, evitando alucinações.

---

## 🔄 Fluxo do LangGraph

```
Mensagem
   ↓
Classificar intenção
   ├── saudacao  → "Bem-vindo à Barbearia O Brabo!"
   ├── pergunta  → RAG
   ├── agendamento → Fluxo de agendamento
   └── fallback  → "Não entendi, pode reformular?"
```

---

## 📅 Fluxo de Agendamento

```
"quero marcar um horário"
   ↓ Qual dia?
"amanhã"
   ↓ Horários disponíveis: 09h, 10h, 11h...
"10h"
   ↓ Qual serviço?
"corte"
   ↓ Confirma: Corte na terça às 10h?
"sim"
   ↓ Agendamento salvo no banco ✅
```

---

## 🗄️ Modelos do Banco de Dados

- **Cliente** — `telegram_id`, `nome`, `criado_em`
- **Conversa** — `cliente`, `mensagem`, `resposta`, `intencao`, `criado_em`
- **Agendamento** — `cliente`, `servico`, `data`, `horario`, `status`, `criado_em`

---

## 📝 Atualizando a Base de Conhecimento

Edite o arquivo `data/barbearia.txt` e reindexe:

```bash
python rag/ingest.py
```

---
