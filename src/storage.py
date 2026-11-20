# src/storage.py
import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "data")
STORAGE_FILE = os.path.join(DATA_DIR, "conversations.json")


def _ensure_storage():
    """Asegura que el directorio y el archivo JSON de historial existan."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_all_conversations() -> dict:
    """Carga todas las conversaciones guardadas desde disco."""
    _ensure_storage()
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_all_conversations(conversations: dict) -> None:
    """Guarda el diccionario completo de conversaciones en disco."""
    _ensure_storage()
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)


def create_conversation(profile: str) -> str:
    """Crea una nueva conversación vacía asociada a un perfil y retorna su ID."""
    conversations = load_all_conversations()
    chat_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    conversations[chat_id] = {
        "id": chat_id,
        "title": "Nueva conversación",
        "profile": profile,
        "messages": [],
        "tokens": {"input": 0, "output": 0, "total": 0},
        "created_at": now,
        "updated_at": now,
    }
    save_all_conversations(conversations)
    return chat_id


def update_conversation(
    chat_id: str,
    messages: list[dict],
    profile: str,
    tokens: dict | None = None,
) -> None:
    """Actualiza los mensajes, el perfil, el título automático y los tokens de un chat."""
    conversations = load_all_conversations()
    if chat_id not in conversations:
        return

    chat = conversations[chat_id]
    chat["messages"] = messages
    chat["profile"] = profile
    chat["updated_at"] = datetime.now().isoformat()

    if tokens:
        chat["tokens"] = tokens

    # Generar título automático a partir del primer mensaje del usuario
    if messages and chat["title"] == "Nueva conversación":
        first_user_msg = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )
        if first_user_msg:
            clean_title = first_user_msg.strip().replace("\n", " ")
            chat["title"] = (
                clean_title[:36] + "..." if len(clean_title) > 36 else clean_title
            )

    save_all_conversations(conversations)


def delete_conversation(chat_id: str) -> None:
    """Elimina una conversación por su ID."""
    conversations = load_all_conversations()
    if chat_id in conversations:
        del conversations[chat_id]
        save_all_conversations(conversations)