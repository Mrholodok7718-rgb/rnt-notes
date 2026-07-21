from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime

# Локальные импорты
from models import Base, Note, User, NoteLink
from schemas import SyncPayload, NoteResponse
from security import get_current_user
from database import get_db, engine
from auth import router as auth_router

app = FastAPI(title="RNT Notes Core API", version="1.0.0")

# Подключаем роутер авторизации
app.include_router(auth_router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # В продакшене эту строку нужно убрать и использовать Alembic
        await conn.run_sync(Base.metadata.create_all)

@app.get("/", tags=["System"])
async def health_check():
    """Системный эндпоинт для проверки доступности узла"""
    return {
        "service": "RNT Notes Core",
        "status": "operational",
        "architecture": "Zero-Knowledge E2EE",
        "version": "1.0.0"
    }

@app.post("/api/v1/sync", response_model=List[NoteResponse])
async def sync_notes(
    payload: SyncPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Асинхронный эндпоинт для батч-синхронизации заметок.
    Реализует Zero-Trust подход: сервер не парсит содержимое.
    """
    synced_notes = []
    
    # 1. Обработка заметок (Upsert логика)
    for note_data in payload.notes:
        stmt = select(Note).where(Note.id == note_data.id, Note.owner_id == current_user.id)
        result = await db.execute(stmt)
        existing_note = result.scalars().first()

        if existing_note:
            # Разрешение конфликтов: Last Write Wins (по версии)
            if note_data.version > existing_note.version:
                existing_note.encrypted_payload = note_data.encrypted_payload
                existing_note.nonce = note_data.nonce
                existing_note.encrypted_embedding = note_data.encrypted_embedding
                existing_note.version = note_data.version
                synced_notes.append(existing_note)
        else:
            new_note = Note(
                id=note_data.id,
                owner_id=current_user.id,
                encrypted_payload=note_data.encrypted_payload,
                nonce=note_data.nonce,
                encrypted_embedding=note_data.encrypted_embedding,
                version=note_data.version
            )
            db.add(new_note)
            synced_notes.append(new_note)

    # 2. Обновление графа (связей)
    for edge in payload.edges:
        stmt = select(NoteLink).where(
            NoteLink.source_id == edge.source_id, 
            NoteLink.target_id == edge.target_id,
            NoteLink.owner_id == current_user.id
        )
        result = await db.execute(stmt)
        if not result.scalars().first():
            new_link = NoteLink(
                owner_id=current_user.id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                encrypted_relation=edge.encrypted_relation
            )
            db.add(new_link)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Sync failed due to database constraint"
        )
    
    return synced_notes

@app.get("/api/v1/notes", response_model=List[NoteResponse])
async def get_all_notes(
    since: datetime = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отдает только те заметки, которые изменились с момента last_sync_time.
    """
    query = select(Note).where(Note.owner_id == current_user.id)
    if since:
        query = query.where(Note.updated_at >= since)
        
    result = await db.execute(query)
    return result.scalars().all()