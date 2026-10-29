from src.db import get_connection
from src.embeddings import embed


def search_incidents(query: str, limit: int = 2):
    query_embedding = embed(query).tolist()

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    id,
                    area,
                    description,
                    ROUND(
                        (1 - (embedding <=> %s::vector))::numeric,
                        3
                    ) AS similarity
                FROM incidents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
            (query_embedding, query_embedding, limit),
        )

        return cur.fetchall()


if __name__ == "__main__":
    query = "Las luces de la calle fallan y se apagan a ratos"

    print(f"Query: {query}\n")

    for incident_id, area, description, similarity in search_incidents(query):
        print(f"{incident_id} | {area} | Similarity: {similarity}")
        print(f"  {description}\n")
