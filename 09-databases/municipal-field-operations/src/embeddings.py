from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.db import get_connection

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model():
    return SentenceTransformer(MODEL_NAME)


def embed(texts):
    return _get_model().encode(texts, normalize_embeddings=True)


def generate_embeddings():
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

    print(f"Embeddings generated: {len(incidents)}")


if __name__ == "__main__":
    generate_embeddings()
