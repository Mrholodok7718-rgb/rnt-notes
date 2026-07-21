import os
import glob
import math
import ollama

class RNTAIEngine:
    """
    Модуль семантического поиска RNT.
    Использует локальную модель для генерации эмбеддингов и поиска по смыслу.
    """
    def __init__(self, vault_path="RNT_Vault", model="nomic-embed-text"):
        self.vault_path = vault_path
        self.model = model
        self.embeddings_db = {}  # Кэш: {file_path: [вектор]}
        
        # Проверяем доступность модели при старте
        try:
            ollama.embeddings(model=self.model, prompt="init")
            self.ready = True
        except Exception as e:
            print(f"[AI Ошибка] Ollama не запущена или модель {self.model} не скачана.")
            self.ready = False

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Математическое вычисление близости двух векторов"""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def build_index(self):
        """Векторизация всех Markdown файлов в хранилище"""
        if not self.ready:
            return

        print("[AI] Индексация графа заметок...")
        md_files = glob.glob(os.path.join(self.vault_path, "*.md"))
        
        for file_path in md_files:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                
            if text:
                response = ollama.embeddings(model=self.model, prompt=text)
                self.embeddings_db[file_path] = response['embedding']
        
        print(f"[AI] Проиндексировано файлов: {len(self.embeddings_db)}")

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Семантический поиск по проиндексированному графу"""
        if not self.ready or not self.embeddings_db:
            return []

        # Превращаем запрос пользователя в вектор
        query_embed = ollama.embeddings(model=self.model, prompt=query)['embedding']
        
        results = []
        for file_path, doc_embed in self.embeddings_db.items():
            sim = self._cosine_similarity(query_embed, doc_embed)
            results.append((file_path, sim))
            
        # Сортируем от самых релевантных к наименее
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]