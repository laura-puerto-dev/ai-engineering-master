# Northfern Technologies — Company Profile

> **Status:** Approved baseline (v0.2)
> **Purpose:** Internal project design reference for Policy Consultant.
> **Important:** Northfern Technologies and all associated people, policies, and employee records are fictional. This document is **not** part of the RAG knowledge corpus.

## 1. Company overview

| Attribute | Description |
|---|---|
| Company | Northfern Technologies |
| Industry | Enterprise software and technology services (B2B) |
| Founded | 2012 |
| Employees | Approximately 850 |
| Countries | Spain, England (United Kingdom), and Mexico |
| Headquarters | Spain |

Northfern Technologies develops enterprise software and provides technology services to other businesses. Its main areas include systems integration, process automation, cloud platforms, and applied artificial intelligence.

The company has engineering, commercial, and corporate teams across its three countries.

## 2. Geographic distribution

| Country | Employees | Main activities |
|---|---:|---|
| Spain | 400 | Headquarters, software development, and operations |
| England (UK) | 250 | Software development and UK customer relationships |
| Mexico | 200 | Software development, support, and operations |
| **Total** | **850** | |

Each country has its own Human Resources team and local policies. Global policies may apply across the organization, subject to explicitly documented local exceptions.

**Implementation scope:** The initial policy corpus covers Spain, England, and Mexico. Structured employee data and implementation features will be introduced incrementally.

## 3. Departments and organizational structure

The company has six common departments:

1. Engineering
2. Product & Design
3. Sales & Marketing
4. Customer Success
5. Finance & Operations
6. Human Resources

Each employee belongs to a country and a department and has an assigned direct manager where applicable.

**Department and access role are separate concepts.** For example, an Engineering employee may also be a manager. HR access is governed by the employee's authorized role and country, not merely by a department label.

## 4. Access roles and boundaries

Policy Consultant will initially support three access roles:

| Role | Intended access |
|---|---|
| Employee | Applicable global and local policies; own authorized personal records |
| Manager | Employee access plus manager-specific policies and authorized records of direct reports |
| Local HR | Applicable policies, HR-restricted policies, and authorized employee records **within their own country** |

Core rules:

- Country and role restrictions apply to both document retrieval and structured-data queries.
- A manager's additional access is limited to their direct reports; being a manager does not grant unrestricted employee-data access.
- Local HR access does not extend to employees or restricted HR content in other countries.
- The application must enforce authorization on the backend, independently of the LLM's decisions.
- Demonstration identities will be selected through the UI, with backend-controlled demo sessions. This is **not** intended to represent production-grade authentication.

## 5. Policy model

The knowledge base will distinguish between:

- **Global policies:** company-wide guidance.
- **Local policies:** country-specific rules and explicit exceptions to global policies.
- **Role-restricted policies:** documents intended for managers or local HR staff.

Policy documents should carry sufficient metadata to support retrieval and access control, including:

- Geographic scope
- Authorized audience or role
- Version
- Effective date and, where relevant, superseded/expiration date
- Relationship to other policies, including explicit local exceptions

The corpus will be fictional but internally consistent. Spanish and Mexican local policies will be written in Spanish, English local policies in English, and global policies in English. The assistant may receive questions in either language; language does not determine the authorized country scope. It is not intended to reproduce or provide authoritative advice on Spanish, English, or Mexican employment law.

## 6. Structured employee data

The initial Spanish dataset will contain fictional records sufficient for read-only queries, including:

- Employee ID and name
- Country and department
- Direct manager relationship
- Employment start date and contract type
- Vacation balances and transactions
- Recorded absences and leave

Payroll, medical information, and bank details are excluded from the initial scope.

Policy Consultant will be able to combine evidence from policy documents with authorized read-only SQL results. For example, a question about remaining vacation days and whether they can be taken in December requires both a personal balance query and the applicable vacation policy.

## 7. Initial demonstration personas

| Name | Country | Role | Primary scenario |
|---|---|---|---|
| Elena Martín | Spain | Employee | Consult applicable policies and personal vacation balance |
| Daniel Ruiz | Spain | Manager | Consult manager policies and authorized direct-report information |
| Sofía López | Spain | Local HR | Consult HR-restricted procedures and authorized Spanish employee records |
| Oliver Bennett | England (UK) | Employee | Demonstrate country-level access isolation and cross-language policy questions |

All names and identities are fictional. Additional employees and reporting relationships will be defined when building the structured dataset.

## 8. Project boundaries

**In scope:**

- Evidence-grounded HR policy Q&A using RAG, evolving into corrective RAG (CRAG)
- Authorized, read-only queries over structured employee data
- Combined document and structured-data answers
- Role-, country-, and reporting-line-aware access control
- Evaluation, observability, and an interactive demonstration interface

**Out of scope for the initial release:**

- Requesting, approving, or changing vacation or leave
- Updating employee records
- Integrating with real HR systems
- Real employee information
- Full production authentication

## 9. Document ownership and location

This file is a **project design artifact**, not a source document for retrieval.

Planned repository path:

`10-11-rag-crag/policy-consultant/docs/company-profile.md`

Company policy documents are stored separately under `data/corpus/`.

## 10. Geographic codes and language conventions

- Spain: `ES`; local policy language: Spanish.
- Mexico: `MX`; local policy language: Spanish.
- England: `GB` as the ISO country code for the United Kingdom, with an explicit `England` jurisdiction/scope field when needed; local policy language: English. **`GB` alone must not be interpreted as covering all UK nations.**
- Global policies: English, with explicitly documented country-specific exceptions.
- User questions and answers may be in Spanish or English. Retrieval must respect the authenticated demo identity's authorized country and role, regardless of the query language.
- The initial policy corpus covers Spain, England, and Mexico. The structured employee dataset will initially focus on Spain.

## 11. Evolution

This profile is the approved starting point, not an immutable specification. Any later changes to company rules, access boundaries, or demonstration data should be reflected here to keep the corpus, SQL dataset, and evaluation cases consistent.
