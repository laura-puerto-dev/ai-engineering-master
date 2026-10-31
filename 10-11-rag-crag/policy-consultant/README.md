# Policy Consultant — RAG & CRAG

An AI-powered policy assistant for **Northfern Technologies**, a fictional multinational company operating in Spain, Mexico, and England.

The project explores how Retrieval-Augmented Generation (RAG) and Corrective RAG (CRAG) can provide evidence-grounded answers to employee questions while respecting country-specific policies and role-based access restrictions.

## Current Status

**Phase 1 — Policy corpus completed**

- 12 fictional corporate policy documents.
- Country-specific and global policies in Spanish and English.
- Different access levels for employees, managers, and HR.

## Planned Features

- Document retrieval with country and role-based authorization.
- RAG with source citations.
- Corrective RAG for evaluating retrieved evidence.
- Authorized read-only SQL queries for employee-specific information.
- Evaluation of retrieval quality, groundedness, and access restrictions.

## Project Structure

- `data/corpus/` — Corporate policy documents.
- `docs/` — Company background and corpus design documentation.

## Disclaimer

All company information, policies, and employee data used in this project are fictional.
