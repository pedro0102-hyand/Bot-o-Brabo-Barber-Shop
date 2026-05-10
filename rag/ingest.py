import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.pipeline import criar_vectorstore

if __name__ == "__main__":
    print("🔄 Iniciando ingestão dos dados...")
    criar_vectorstore()
    print("✅ Dados indexados com sucesso!")