from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Публичный ключ для E2E шаринга
    public_key = Column(Text, nullable=True)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    encrypted_payload = Column(Text, nullable=False)
    nonce = Column(String, nullable=False)
    encrypted_embedding = Column(Text, nullable=True)
    
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class NoteLink(Base):
    __tablename__ = "note_links"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    source_id = Column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    target_id = Column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    encrypted_relation = Column(String, nullable=False)
    
    __table_args__ = (UniqueConstraint('source_id', 'target_id', name='_source_target_uc'),)