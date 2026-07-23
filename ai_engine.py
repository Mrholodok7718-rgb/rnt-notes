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

    def ask_copilot(self, query: str, context_results: list[tuple[str, float]], llm_model="llama3") -> str:
        """Генерация ответа на основе найденного контекста (RAG)"""
        if not self.ready:
            return "[CRITICAL] Локальная ИИ-модель недоступна."

        # Формируем контекст из найденных заметок
        context_text = ""
        for file_path, score in context_results:
            if score >= 0.4:  # Берем только уверенные совпадения
                with open(file_path, "r", encoding="utf-8") as f:
                    filename = os.path.basename(file_path)
                    # Ограничиваем срез, чтобы не перегрузить контекстное окно модели
                    context_text += f"\n--- Файл: {filename} ---\n{f.read().strip()[:1500]}\n"

        if not context_text:
            return "В текущей базе знаний RNT не найдено релевантных данных по этому запросу."

        prompt = (
            "Ты — локальный AI-ассистент системы RNT Notes. Твоя задача — отвечать на вопросы, "
            "опираясь ИСКЛЮЧИТЕЛЬНО на предоставленный ниже контекст из зашифрованных локальных заметок.\n\n"
            f"КОНТЕКСТ БАЗЫ ЗНАНИЙ:\n{context_text}\n\n"
            f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {query}\n\n"
            "ОТВЕТ:"
        )

        try:
            print(f"[AI] RAG-генерация через {llm_model}...")
            response = ollama.generate(model=llm_model, prompt=prompt)
            return response.get("response", "[Ошибка генерации]")
        except Exception as e:
            return f"[Ошибка LLM]: {str(e)}"
            
    def find_related_notes(self, text: str, current_file_path: str, threshold: float = 0.85) -> list[str]:
        """Анализирует текст и ищет похожие заметки по вектору сходства"""
        if not self.ready or not self.embeddings_db:
            return []

        try:
            # Берем первые 2000 символов, чтобы не перегружать контекст Ollama
            query_embed = ollama.embeddings(model=self.model, prompt=text[:2000])['embedding']
        except Exception as e:
            print(f"[AI] Ошибка векторизации для связей: {e}")
            return []
        
        related = []
        for file_path, doc_embed in self.embeddings_db.items():
            if file_path == current_file_path:
                continue
            
            sim = self._cosine_similarity(query_embed, doc_embed)
            if sim >= threshold:  # Если совпадение больше 85%
                filename = os.path.basename(file_path).replace(".md", "")
                related.append(filename)
        
        return related