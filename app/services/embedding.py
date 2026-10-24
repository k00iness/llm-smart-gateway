from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        # Chargement du modèle léger all-MiniLM-L6-v2
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

    def generate_embedding(self, text: str) -> list[float]:
        """Génère un vecteur d'embedding à partir d'un texte."""
        if not text.strip():
            return []
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# Instance unique (Singleton) pour éviter de recharger le modèle à chaque requête
embedding_service = EmbeddingService()