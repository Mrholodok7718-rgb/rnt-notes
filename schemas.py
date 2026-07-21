from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

class NoteBase(BaseModel):
    # ID генерируется на клиенте (оффлайн-first подход)
    id: UUID = Field(default_factory=uuid4)
    # Зашифрованный JSON (заголовок, теги, контент)
    encrypted_payload: str = Field(..., description="AES-256-GCM encrypted note data")
    nonce: str = Field(..., description="Cryptographic nonce for decryption")
    # Векторное представление (генерируется локально, шифруется, используется для AI)
    encrypted_embedding: Optional[str] = None
    version: int = Field(default=1)

class NoteCreate(NoteBase):
    pass  # Пустой класс-наследник требует pass, чтобы избежать синтаксической ошибки

class NoteResponse(NoteBase):
    owner_id: UUID
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GraphEdge(BaseModel):
    source_id: UUID
    target_id: UUID
    # Тип связи тоже зашифрован
    encrypted_relation: str

class SyncPayload(BaseModel):
    last_sync_time: datetime
    notes: List[NoteCreate]
    edges: List[GraphEdge]

# --- Схемы авторизации ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    # Публичный ключ (RSA/ECC) для E2E шаринга заметок между пользователями
    public_key: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str