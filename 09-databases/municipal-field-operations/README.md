# Municipal Field Operations

**Secure Semantic & Geospatial Incident Search**

A Python and PostgreSQL project exploring how municipal maintenance teams can find relevant incidents near their current location while enforcing department-level data isolation.

## Business Context

Municipal maintenance workers often travel between different areas to resolve reported incidents.

When an employee is already working in a particular location, identifying other pending incidents nearby can help organize interventions and reduce unnecessary travel.

This project simulates municipal maintenance operations in Teruel, Spain, using fictional incident data.

## Project Goals

- Find semantically similar incidents using pgvector.
- Filter incidents by geographic proximity using PostGIS.
- Enforce department-level data isolation using PostgreSQL Row-Level Security (RLS).
- Demonstrate that employees cannot access incidents belonging to other departments.

## Departments

- Electricity
- Gardening
- Cleaning
- Public Works

## Tech Stack

- Python 3.12 and uv
- PostgreSQL 17
- pgvector
- PostGIS
- Docker Compose

## Project Status

Initial project setup. Database schema, incident ingestion, semantic search, geospatial filtering, and RLS policies are planned.

## Academic Context

Developed for Module 09 — Databases for AI Agents, as part of the AI Engineering Master's program.
