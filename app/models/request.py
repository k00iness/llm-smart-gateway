from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Le rôle du message (system, user, assistant)")
    content: str = Field(..., description="Le contenu texte du message")


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(default=None, description="Modèle demandé par le client")
    messages: List[ChatMessage] = Field(..., description="Liste de l'historique des messages")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: Optional[bool] = Field(default=False, description="Activer le mode streaming")
    user_id: Optional[str] = Field(default="default_user", description="Identifiant du client pour le Rate Limiting")

    def get_last_user_message(self) -> str:
        """Extrait le dernier message de l'utilisateur pour le cache sémantique."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return ""