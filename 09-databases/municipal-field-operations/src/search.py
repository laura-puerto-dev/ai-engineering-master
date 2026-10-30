from src.db import get_app_connection, get_connection
from src.embeddings import embed


def search_incidents(query: str, limit: int = 2):
    """Find incidents ranked by semantic similarity to `query`, regardless of location or status."""
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


def search_nearby_incidents(
    query: str,
    latitude: float,
    longitude: float,
    department_id: int,
    radius_meters: int = 1000,
    limit: int = 2,
    status: str = "pending",
):
    """Find incidents near a location, ranked by semantic similarity to `query`.

    Use case: a field operator wants to know what they can act on near their
    current position. Defaults to 'pending' because resolved incidents aren't
    relevant to this view. Other statuses can be requested explicitly.
    """
    query_embedding = embed(query).tolist()

    with get_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.department_id', %s, true)",
            (str(department_id),),
        )
        cur.execute(
            """
                SELECT
                    id,
                    area,
                    description,
                    ROUND(
                        (1 - (embedding <=> %s::vector))::numeric,
                        3
                    ) AS similarity,
                    ROUND(
                        ST_Distance(
                            location,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        )::numeric,
                        0
                    ) AS distance_meters
                FROM incidents
                WHERE embedding IS NOT NULL
                  AND status = %s
                  AND ST_DWithin(
                      location,
                      ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                      %s
                  )
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
            (
                query_embedding,
                longitude,
                latitude,
                status,
                longitude,
                latitude,
                radius_meters,
                query_embedding,
                limit,
            ),
        )

        return cur.fetchall()


if __name__ == "__main__":
    query = "Hay ramas que dificultan el paso por la acera"
    latitude = 40.34281
    longitude = -1.10704
    radius_meters = 1000
    department_id = 3  # Gardening

    results = search_nearby_incidents(
        query=query,
        latitude=latitude,
        longitude=longitude,
        department_id=department_id,
        radius_meters=radius_meters,
    )

    print("Ubicación: Plaza del Torico, Teruel")
    print(f"Radio de búsqueda: {radius_meters} metros (en línea recta)")
    print(f"Consulta: {query}\n")

    for incident_id, area, description, similarity, distance in results:
        print(
            f"{incident_id} | {area} | "
            f"Similitud: {similarity} | Distancia: {distance} m"
        )
        print(f"  {description}\n")
