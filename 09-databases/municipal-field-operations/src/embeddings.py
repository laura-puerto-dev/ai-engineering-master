from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.db import get_connection

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the sentence transformer model for reuse."""
    return SentenceTransformer(MODEL_NAME)


def embed(texts):
    """Generate normalized embeddings for one or more texts.

    A single string produces a 1D vector, while a list of strings
    produces a 2D array containing one vector per text.
    """
    return _get_model().encode(texts, normalize_embeddings=True)


def generate_embeddings():
    """Generate and store embeddings for all incident descriptions.

    Existing embeddings are overwritten to keep them consistent
    with the current descriptions and embedding model.
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, description FROM incidents ORDER BY id")
        incidents = cur.fetchall()

        descriptions = [description for _, description in incidents]
        embeddings = embed(descriptions)

        for (incident_id, _), embedding in zip(incidents, embeddings):
            cur.execute(
                """
                    UPDATE incidents
                    SET embedding = %s::vector
                    WHERE id = %s
                    """,
                (embedding.tolist(), incident_id),
            )

    print(f"Embeddings generados: {len(incidents)}")


if __name__ == "__main__":
    generate_embeddings()
