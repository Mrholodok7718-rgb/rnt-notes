import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class RNTClientCrypto:
    """
    Модуль E2E шифрования для клиента RNT Notes.
    Использует AES-256-GCM для данных и PBKDF2 для деривации ключа.
    """
    def __init__(self, master_password: str, salt: bytes = None):
        # В реальном приложении соль пользователя должна храниться локально или выдаваться сервером (без секрета)
        self.salt = salt or os.urandom(16)
        
        # Защита от брутфорса: 600 000 итераций SHA-256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=600_000,
        )
        self.key = kdf.derive(master_password.encode('utf-8'))
        self.aesgcm = AESGCM(self.key)

    def encrypt_note(self, plaintext: str) -> tuple[str, str]:
        """
        Шифрует Markdown текст заметки.
        Возвращает кортеж: (зашифрованный payload в Base64, nonce в Base64)
        """
        nonce = os.urandom(12)  # Рекомендованный размер для GCM
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        payload_b64 = base64.b64encode(ciphertext).decode('utf-8')
        nonce_b64 = base64.b64encode(nonce).decode('utf-8')
        
        return payload_b64, nonce_b64

    def decrypt_note(self, ciphertext_b64: str, nonce_b64: str) -> str:
        """
        Расшифровывает данные, полученные с сервера.
        """
        ciphertext = base64.b64decode(ciphertext_b64)
        nonce = base64.b64decode(nonce_b64)
        
        plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode('utf-8')

# --- Интеграционный тест модуля ---
if __name__ == "__main__":
    print("--- Тестирование криптографического ядра ---")
    password = "MySuperSecretMasterPassword"
    
    # Имитация создания заметки на клиенте
    original_markdown = "# Идея архитектуры\nНам нужно интегрировать Ollama для локального графа связей."
    print(f"[Текст]: {original_markdown}\n")
    
    # 1. Инициализация (соль должна быть сохранена)
    crypto = RNTClientCrypto(password)
    salt_b64 = base64.b64encode(crypto.salt).decode('utf-8')
    
    # 2. Шифрование перед отправкой на бэкенд
    encrypted_payload, nonce = crypto.encrypt_note(original_markdown)
    print(f"[Шифр Payload]: {encrypted_payload[:40]}...")
    print(f"[Шифр Nonce]: {nonce}")
    
    # 3. Дешифровка после загрузки с бэкенда
    # (Используем ту же соль для восстановления ключа из пароля)
    client_decoder = RNTClientCrypto(password, salt=base64.b64decode(salt_b64))
    decrypted_markdown = client_decoder.decrypt_note(encrypted_payload, nonce)
    
    print(f"\n[Расшифровано]: {decrypted_markdown}")
    assert original_markdown == decrypted_markdown
    print("\n[+] E2E шифрование работает корректно. Утечек нет.")