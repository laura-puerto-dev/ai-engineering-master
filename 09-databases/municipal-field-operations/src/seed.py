import json
from pathlib import Path

from src.db import get_connection

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "incidents.json"


def seed_database():
    incidents = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    with get_connection() as conn, conn.cursor() as cur:
        departments = sorted({incident["department"] for incident in incidents})

        for department in departments:
            cur.execute(
                """
                    INSERT INTO departments (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                (department,),
            )

        cur.execute("SELECT id, name FROM departments")
        department_ids = {name: id for id, name in cur.fetchall()}

        for incident in incidents:
            cur.execute(
                """
                    INSERT INTO incidents (
                        id, department_id, area, description, status, location
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        department_id = EXCLUDED.department_id,
                        area = EXCLUDED.area,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        location = EXCLUDED.location
                    """,
                (
                    incident["id"],
                    department_ids[incident["department"]],
                    incident["area"],
                    incident["description"],
                    incident["status"],
                    incident["longitude"],
                    incident["latitude"],
                ),
            )

    print(f"Dataset processed: {len(incidents)} incidents")


if __name__ == "__main__":
    seed_database()
