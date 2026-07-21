import requests
import uuid
from datetime import datetime, timezone
import base64
from client_crypto import RNTClientCrypto

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_test():
    print("--- 1. Инициализация E2E Клиента ---")
    password = "StrictPassword2026!"
    
    # В реальном десктоп-клиенте соль генерируется один раз и хранится в локальной БД (без нее ключ не восстановить)
    crypto = RNTClientCrypto(master_password=password)
    
    # 2. Авторизация на бэкенде
    print("\n--- 2. Авторизация на сервере ---")
    auth_data = {
        "username": "rnt_admin",
        "password": password,
        "public_key": "dummy_rsa_pub_key"
    }
    
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=auth_data)
    if r.status_code == 400:
        r = requests.post(
            f"{BASE_URL}/api/v1/auth/login", 
            data={"username": auth_data["username"], "password": auth_data["password"]}
        )
    
    token = r.json().get("access_token")
    if not token:
        print("[Критическая Ошибка] Не удалось получить токен.")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    print("[+] Сессия открыта.")

    # 3. Локальное шифрование
    print("\n--- 3. Локальное шифрование (Zero-Knowledge) ---")
    plaintext_note = "# Архитектура RNT Notes\nРазвертывание zero-knowledge графа с интеграцией локальных моделей Ollama для семантического поиска."
    print(f"Оригинальный текст:\n{plaintext_note}")
    
    encrypted_payload, nonce = crypto.encrypt_note(plaintext_note)
    note_id = str(uuid.uuid4())
    
    # 4. Отправка на сервер
    print("\n--- 4. Отправка зашифрованного блоба в сеть ---")
    sync_payload = {
        "last_sync_time": datetime.now(timezone.utc).isoformat(),
        "notes": [{
            "id": note_id,
            "encrypted_payload": encrypted_payload,
            "nonce": nonce,
            "encrypted_embedding": None,
            "version": 1
        }],
        "edges": []
    }
    
    r = requests.post(f"{BASE_URL}/api/v1/sync", json=sync_payload, headers=headers)
    print(f"Статус сервера: {r.status_code}")

    # 5. Получение и расшифровка
    print("\n--- 5. Чтение с сервера и дешифровка на лету ---")
    r = requests.get(f"{BASE_URL}/api/v1/notes", headers=headers)
    server_notes = r.json()
    
    # Ищем нашу новую заметку среди всех
    target_note = next((n for n in server_notes if n["id"] == note_id), None)
    
    if target_note:
        print(f"[Сервер отдал шифр]: {target_note['encrypted_payload'][:50]}...")
        decrypted_text = crypto.decrypt_note(target_note["encrypted_payload"], target_note["nonce"])
        print(f"\n[Расшифровано клиентом]:\n{decrypted_text}")
    else:
        print("Заметка не найдена на сервере!")

if __name__ == "__main__":
    try:
        run_e2e_test()
    except Exception as e:
        print(f"[Ошибка] {e}")