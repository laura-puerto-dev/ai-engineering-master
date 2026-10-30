# Municipal Field Operations

**Secure Semantic & Geospatial Incident Search with PostgreSQL, pgvector, PostGIS, and Row-Level Security**

A Python and PostgreSQL project demonstrating how municipal maintenance teams can find relevant incidents near their current location while enforcing department-level data isolation.

Built with **PostgreSQL 17, pgvector, PostGIS, Python 3.12, and Sentence Transformers**.

## Business Context

Municipal maintenance workers often travel between different areas to resolve reported incidents.

When an employee is already working in a particular location, identifying other pending incidents nearby can help organize interventions, reduce unnecessary travel, and make better use of field teams' time.

However, proximity alone is not enough.

A gardening operator looking for incidents involving tree branches should not receive unrelated maintenance tasks or incidents belonging to other departments, even when those incidents are geographically close or semantically similar.

This project simulates municipal maintenance operations in **Teruel, Spain**, using fictional incident data to explore how semantic search, geographic filtering, and database-level access control can work together.

## Project Goals

The project demonstrates how to:

- Find semantically similar incidents using multilingual text embeddings and **pgvector**.
- Filter incidents by geographic proximity using **PostGIS**.
- Prioritize pending incidents relevant to a field operator's current location.
- Enforce department-level data isolation using **PostgreSQL Row-Level Security (RLS)**.
- Compare identical queries with and without RLS to demonstrate that relevance and proximity never override access restrictions.
- Reproduce the entire workflow locally using Docker Compose and Python.

## Architecture

```text
Fictional municipal incidents (JSON)
                |
                v
         Python ingestion
                |
                v
     PostgreSQL + PostGIS
                |
                +------> Incident descriptions
                |              |
                |              v
                |       Sentence Transformers
                |              |
                |              v
                |        384-dimensional
                |           embeddings
                |              |
                v              v
         PostgreSQL + pgvector
                |
                v
          Search request
                |
                +--> Department context (RLS)
                +--> Pending status
                +--> Geographic radius (PostGIS)
                +--> Semantic similarity (pgvector)
                |
                v
       Ranked, authorized incidents
```

The application generates embeddings in Python and performs filtering and ranking directly in PostgreSQL.

The database is responsible for enforcing department isolation, rather than relying on a department filter added by application code.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Incident ingestion, embedding generation, and search execution |
| PostgreSQL 17 | Relational storage and SQL query execution |
| pgvector | Vector storage and cosine similarity search |
| PostGIS | Geographic coordinates, radius filtering, and distance calculations |
| Sentence Transformers | Multilingual text embeddings |
| Psycopg 3 | PostgreSQL connectivity |
| Docker Compose | Reproducible local database environment |
| uv | Python dependency and virtual environment management |
| Ruff | Python linting and formatting |
| MyPy | Static type checking |

**Embedding model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

The model produces **384-dimensional embeddings**. Incident descriptions and search queries are encoded using the same model.

Embeddings are normalized before being stored or used for retrieval.

## Dataset

The project includes **20 fictional incidents** distributed across four municipal departments in Teruel.

| Department | Incidents | Examples |
|---|---:|---|
| Cleaning | 5 | Waste collection, abandoned furniture, street cleaning |
| Electricity | 5 | Street lighting and electrical infrastructure |
| Gardening | 5 | Trees, branches, irrigation, green spaces |
| Public Works | 5 | Roads, pavements, public infrastructure |

Each incident contains:

- A unique identifier.
- Its assigned department.
- A geographic area.
- A Spanish-language description.
- An operational status.
- Geographic coordinates (latitude and longitude).

The incident embeddings are generated separately and stored in PostgreSQL.

The dataset deliberately includes incidents from different departments with similar descriptions and nearby locations. This makes it possible to demonstrate why semantic similarity alone is insufficient when access restrictions apply.

All incidents are fictional. Geographic references are based on locations in Teruel.

## Search Pipeline

The search combines several conditions in a single PostgreSQL query.

### 1. Department-level authorization

The application connects using a restricted database role and establishes the operator's department context.

PostgreSQL RLS determines which incident rows are visible to that role.

### 2. Operational status

The field-operator search defaults to incidents with status `pending`.

Resolved incidents are not relevant to the default nearby-work workflow.

The `status` parameter defaults to `pending` but can be changed to retrieve incidents in other states, such as `resolved`, without modifying the SQL query.

### 3. Geographic proximity

PostGIS filters incidents using `ST_DWithin`, based on the operator's coordinates and a radius expressed in meters.

Distances are calculated using `ST_Distance`.

The `geography` type provides geographic distances in meters, rather than treating latitude and longitude as planar coordinates.

These distances represent geographic proximity, **not driving or walking routes**.

### 4. Semantic similarity

The query is converted into an embedding using the same multilingual model used for incident descriptions.

pgvector compares embeddings using cosine distance:

```sql
embedding <=> query_embedding
```

The project converts cosine distance into a similarity score:

```text
similarity = 1 - cosine_distance
```

For the RLS comparison example, a minimum similarity threshold of `0.5` removes incidents that are insufficiently related to the query.

This threshold is illustrative. It has not been calibrated using a labeled evaluation dataset.

### 5. Ranking and result limit

Matching incidents are ordered by semantic similarity, from highest to lowest.

The SQL `LIMIT` clause establishes the maximum number of returned incidents.

For example, `LIMIT 10` returns all matching incidents if fewer than 10 satisfy the filters, or the 10 highest-ranked incidents if more than 10 qualify.

## PostgreSQL Row-Level Security

The project uses **Row-Level Security (RLS)** to enforce department isolation directly in PostgreSQL.

The restricted application role is `municipal_app`.

Its access policy checks the department identifier stored in the current transaction context:

```sql
department_id = NULLIF(
    current_setting('app.department_id', true),
    ''
)::integer
```

The application establishes this context before executing the search:

```python
cur.execute(
    "SELECT set_config('app.department_id', %s, true)",
    (str(department_id),),
)
```

The final argument, `true`, makes the setting transaction-local.

This prevents the department context from intentionally persisting beyond the current transaction.

If the department context is absent, the policy does not match any incidents.

### Security assumptions

This project demonstrates database-level isolation, not a complete authentication or authorization system.

It assumes that a trusted backend:

1. Authenticates the operator.
2. Determines the operator's authorized department.
3. Connects using the restricted application role.
4. Sets the department context before executing the search.

End users must not have direct database access or control the department identifier themselves.

The administrative database role is used only for database setup, data ingestion, embedding generation, and diagnostic comparisons.

The project does not expose administrative queries to end users.

## Demonstrating RLS: Same Query, Different Visibility

One of the main demonstrations in this repository is `examples/compare_rls.py`.

The script executes the **same SQL query with the same parameters**, changing only the database access context:

- **Administrator:** Executes the query using the administrative connection, which bypasses RLS.
- **Gardening operator:** Executes the query using `municipal_app`, with the department context set to Gardening.

Both searches use the same semantic embedding, geographic radius, operational status, similarity threshold, ranking, and result limit.

### Example query

| Parameter | Value |
|---|---|
| Search text | `Hay ramas que dificultan el paso por la acera` |
| Location | Plaza del Torico, Teruel |
| Radius | 1,000 meters |
| Status | `pending` |
| Minimum similarity | 0.5 |
| Maximum results | 10 |
| Restricted department | Gardening |

### Results without RLS

The administrator retrieves five matching incidents:

| Incident | Department | Area | Similarity | Distance |
|---|---|---|---:|---:|
| L05 | Cleaning | Plaza de San Juan | 0.848 | 223 m |
| J05 | Gardening | San León | 0.805 | 571 m |
| V03 | Public Works | Plaza de San Juan | 0.770 | 223 m |
| E04 | Electricity | Plaza del Torico | 0.736 | 0 m |
| J01 | Gardening | Parque de los Fueros | 0.695 | 942 m |

The most semantically relevant incident belongs to Cleaning, not Gardening.

An Electricity incident is located at the search origin itself, but also belongs to a different department.

### Results with RLS enabled for Gardening

The restricted application role retrieves only two incidents:

| Incident | Department | Area | Similarity | Distance |
|---|---|---|---:|---:|
| J05 | Gardening | San León | 0.805 | 571 m |
| J01 | Gardening | Parque de los Fueros | 0.695 | 942 m |

**Three incidents disappear because they belong to other departments, not because their semantic similarity or geographic distance changed.**

This illustrates the core security principle of the project:

> Semantic relevance and geographic proximity must never override authorization boundaries.

The comparison is reproducible with:

```powershell
uv run python -m examples.compare_rls
```

## Getting Started

The following instructions reproduce the project on a local Windows machine using PowerShell, Docker Desktop, and uv.

DBeaver or another graphical database client is optional and is not required.

### Prerequisites

- Docker Desktop with Docker Compose
- Python 3.12
- [uv](https://docs.astral.sh/uv/)

Clone the repository and navigate to the project directory:

```powershell
git clone https://github.com/laura-puerto-dev/ai-engineering-master.git
cd ai-engineering-master/09-databases/municipal-field-operations
```

### Step 1 — Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the database credentials.

For the local setup, the PostgreSQL administrator credentials are used by Docker and the Python ingestion scripts.

The application role credentials are configured separately.

The `.env` file is excluded from Git.

### Step 2 — Start PostgreSQL

```powershell
docker compose up -d
```

Docker starts the PostgreSQL container with pgvector and PostGIS available.

The database runs in a persistent Docker volume.

If port `5432` is already occupied on your machine, change both `POSTGRES_PORT` and `DATABASE_PORT` in `.env` to the same available port before starting the container.

### Step 3 — Create the database schema

Run:

```powershell
Get-Content -Raw sql/01_schema.sql | docker exec -i municipal-field-operations-db psql -v ON_ERROR_STOP=1 -U municipal_admin -d municipal_operations
```

This creates the pgvector and PostGIS extensions and the required database tables.

### Step 4 — Configure the restricted application role and RLS

Run:

```powershell
Get-Content -Raw sql/02_security.sql | docker exec -i municipal-field-operations-db psql -v ON_ERROR_STOP=1 -U municipal_admin -d municipal_operations
```

This script creates the `municipal_app` role, grants the required read permissions, enables RLS on `incidents`, and creates the department isolation policy.

Set a password for the application role:

```powershell
docker exec -it municipal-field-operations-db psql -U municipal_admin -d municipal_operations
```

Inside the PostgreSQL console:

```text
\password municipal_app
```

Enter the password when prompted.

Exit with:

```text
\q
```

Add the password to the local `.env` file:

```dotenv
APP_DATABASE_PASSWORD=your_chosen_password
```

This password is used by the restricted application connection.

### Step 5 — Install Python dependencies

```powershell
uv sync
```

The first embedding operation may download the multilingual model.

### Step 6 — Load incidents

```powershell
uv run python -m src.seed
```

This populates PostgreSQL with the fictional municipal incidents.

### Step 7 — Generate embeddings

```powershell
uv run python -m src.embeddings
```

This generates and stores the vector embeddings for the incident descriptions.

### Step 8 — Run the field-operator search

```powershell
uv run python -m src.search
```

This executes the configured example search for Gardening incidents near Plaza del Torico.

The search uses the restricted application role and PostgreSQL RLS.

### Step 9 — Run the RLS comparison

```powershell
uv run python -m examples.compare_rls
```

The output displays the department, geographic area, incident description, semantic similarity, and distance in meters.

Compare the results from the administrator and Gardening application role to verify department isolation.

## Code Quality

Run the following checks from the project directory:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src examples
```

## Project Scope and Limitations

This is an educational backend project focused on combining PostgreSQL capabilities for AI-assisted operational search.

It includes:

- Fictional municipal incident ingestion.
- Multilingual embedding generation.
- Semantic similarity search.
- Geographic proximity filtering.
- Department isolation with RLS.
- A reproducible security comparison.

It does not include:

- HTTP API endpoints or a frontend.
- User authentication or production identity management.
- A production authorization service.
- Large-scale performance benchmarks.
- Calibrated semantic relevance thresholds.
- Route planning or travel-time estimation.

The small dataset is designed to demonstrate correctness and behavior, not retrieval performance at scale.

## Academic Context

Developed for **Module 09 — Databases for AI Agents**, as part of the AI Engineering Master's program.

## Key Takeaway

A useful field-operations search needs more than semantic relevance.

By combining **pgvector, PostGIS, and PostgreSQL RLS**, this project demonstrates how a single PostgreSQL query can retrieve incidents that are semantically relevant, geographically nearby, and authorized for the requesting department.

The result is a small, reproducible backend example of how semantic retrieval can respect real operational and security constraints.
