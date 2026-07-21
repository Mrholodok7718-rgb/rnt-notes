# ⚡ RNT Notes Core

> **Local-First Zero-Knowledge E2EE Note-Taking System with Local AI Semantic Search.**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-005571?style=flat-square&logo=fastapi&logoColor=white)
![Encryption](https://img.shields.io/badge/Encryption-AES--256--GCM-red?style=flat-square&logo=security&logoColor=white)
![AI](https://img.shields.io/badge/AI-Ollama%20(Local)-orange?style=flat-square&logo=ollama&logoColor=white)

## 🏛️ Архитектура системы

**RNT Notes** спроектирован по принципу **Zero-Trust & Local-First**. 
1. **Obsidian-style Vault:** Все заметки хранятся локально на диске в открытом формате `.md`. Приложение работает полностью в офлайне.
2. **Client-Side E2E Encryption:** Перед синхронизацией с облаком данные шифруются прямо на клиентской машине с использованием алгоритма **AES-256-GCM** и производной ключа **PBKDF2** (600 000 итераций).
3. **Blind Backend:** Сервер на базе **FastAPI + SQLAlchemy (Async)** является "слепым" транспортом. Он не имеет доступа к мастер-паролю и хранит исключительно зашифрованные блобы.
4. **Local AI Engine:** Встроенный поиск использует локальную модель через **Ollama (`nomic-embed-text`)**, рассчитывая косинусное сходство векторов для семантического поиска по смыслу.

---

## 🛠️ Стек технологий

* **Backend:** FastAPI, Uvicorn, SQLAlchemy (Async), Pydantic, Bcrypt, PyJWT.
* **Client UI:** CustomTkinter (Cyber-Minimalism / Glassmorphic UI design).
* **Cryptography:** Python `cryptography` library (AES-GCM, PBKDF2).
* **AI / RAG:** Ollama (Local Embeddings).

---

## 🚀 Быстрый старт

### 1. Клонирование и установка зависимостей
```bash
git clone [https://github.com/](https://github.com/) твой_логин / rnt-notes.git
cd rnt-notes
python -m venv .venv
# Активация виртуального окружения (для Windows PowerShell):
& ".\.venv\Scripts\Activate.ps1"
pip install -r requirements.txt