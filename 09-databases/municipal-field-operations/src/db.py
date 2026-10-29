import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create a PostgreSQL connection using environment variables."""
    return psycopg.connect(
        host=os.environ["DATABASE_HOST"],
        port=os.environ["DATABASE_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
