
-- Required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Municipal departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Municipal employees
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

-- Reported municipal incidents
CREATE TABLE IF NOT EXISTS incidents (
    id VARCHAR(10) PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    area VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    -- other states (e.g. 'resolved') are supported but not seeded in this demo
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    location GEOGRAPHY(Point, 4326),
    embedding VECTOR(384)
);
