from src.db import get_app_connection, get_connection
from src.embeddings import embed

DEPARTMENTS = {
    "cleaning": "LIMPIEZA",
    "electricity": "ELECTRICIDAD",
    "gardening": "JARDINERÍA",
    "public_works": "OBRAS PÚBLICAS",
}

QUERY = "Hay ramas que dificultan el paso por la acera"
LATITUDE = 40.34281
LONGITUDE = -1.10704
RADIUS_METERS = 1000
LIMIT = 10
MIN_SIMILARITY = 0.5
DEPARTMENT_ID = 3  # Gardening

SQL = """
    SELECT
        i.id,
        d.name,
        i.area,
        i.description,
        ROUND(
            (1 - (i.embedding <=> %s::vector))::numeric,
            3
        ) AS similarity,
        ROUND(
            ST_Distance(
                i.location,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            )::numeric,
            0
        ) AS distance_meters
    FROM incidents AS i
    JOIN departments AS d ON d.id = i.department_id
    WHERE i.embedding IS NOT NULL
      AND i.status = 'pending'
      AND (1 - (i.embedding <=> %s::vector)) >= %s
      AND ST_DWithin(
          i.location,
          ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
          %s
      )
    ORDER BY i.embedding <=> %s::vector
    LIMIT %s
"""


def print_results(results):
    """Display incident search results in a readable format."""
    for incident_id, department, area, description, similarity, distance in results:
        department_name = DEPARTMENTS.get(department, department.upper())

        print(f"\n[{incident_id}] {department_name} | {area}")
        print(f"  {description}")
        print(f"  Similitud: {similarity:.3f} | Distancia: {distance:.0f} m")

    print(f"\nTotal: {len(results)} incidencias")


def main():
    """Compare identical searches with and without department-level RLS."""
    query_embedding = embed(QUERY).tolist()

    params = (
        query_embedding,  # SELECT: similarity
        LONGITUDE,  # SELECT: distance longitude
        LATITUDE,  # SELECT: distance latitude
        query_embedding,  # WHERE: similarity
        MIN_SIMILARITY,  # WHERE: minimum similarity
        LONGITUDE,  # WHERE: radius longitude
        LATITUDE,  # WHERE: radius latitude
        RADIUS_METERS,  # WHERE: radius
        query_embedding,  # ORDER BY: similarity
        LIMIT,  # LIMIT
    )

    print(f"Consulta: {QUERY}")
    print("Ubicación: Plaza del Torico, Teruel")
    print(f"Radio: {RADIUS_METERS} m")
    print(f"Similitud mínima: {MIN_SIMILARITY}")

    print("\n=== SIN RLS (ADMINISTRADOR) ===")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(SQL, params)
        print_results(cur.fetchall())

    print("\n=== CON RLS (JARDINERÍA) ===")

    with get_app_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.department_id', %s, true)",
            (str(DEPARTMENT_ID),),
        )
        cur.execute(SQL, params)
        print_results(cur.fetchall())


if __name__ == "__main__":
    main()
