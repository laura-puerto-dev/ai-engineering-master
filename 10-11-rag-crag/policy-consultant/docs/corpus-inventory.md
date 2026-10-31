# Policy Consultant — Corpus Inventory

**Company:** Northfern Technologies (fictional)
**Version:** 0.1
**Status:** Initial corpus completed; all 12 policy documents created
**Project path:** `10-11-rag-crag/policy-consultant/`

## Purpose

This inventory defines the initial knowledge corpus for Policy Consultant, an HR assistant that will evolve from baseline RAG to corrective RAG (CRAG). It is **project design documentation**, not a source document to ingest into the RAG.

All policies, employees, balances, and procedures are fictional. The initial corpus contains 12 policy documents covering Spain, Mexico, England, and global company policies.

## Initial document inventory

| Document ID | Proposed title | Scope | Language | Authorized audience | Purpose |
| --- | --- | --- | --- | --- | --- |
| GLB-001 | Code of Conduct | Global | English | All employees | Company-wide conduct principles |
| GLB-002 | Information Security Policy | Global | English | All employees | Security responsibilities and acceptable practices |
| ES-001 | Vacaciones y días libres | Spain | Spanish | Spain employees | Vacation entitlement, accrual, usage, deadlines, and exceptions |
| ES-002 | Permisos y ausencias | Spain | Spanish | Spain employees | Leave types, absences, and supporting documentation |
| ES-003 | Teletrabajo y flexibilidad | Spain | Spanish | Spain employees | Remote-work arrangements, flexibility, and exceptions |
| ES-004 | Beneficios y formación | Spain | Spanish | Spain employees | Benefits and learning support |
| ES-005 | Viajes y gastos | Spain | Spanish | Spain employees | Travel rules, expense limits, and reimbursement |
| ES-006 | Gestión de ausencias | Spain | Spanish | Spain managers | Manager-only absence handling procedures |
| ES-007 | Procedimientos internos de RR. HH. | Spain | Spanish | Spain HR | Restricted internal HR procedures |
| MX-001 | Vacaciones y permisos | Mexico | Spanish | Mexico employees | Country-specific vacation and leave rules |
| MX-002 | Teletrabajo | Mexico | Spanish | Mexico employees | Country-specific remote-work rules |
| EN-001 | Annual Leave and Time Off | England | English | England employees | Country-specific annual leave and time-off rules |

**Audience interpretation:** “Spain employees” includes eligible employees based in Spain, including managers and HR personnel where applicable; manager-only and HR-only documents require the corresponding role and country. Exact authorization semantics will be defined and tested during implementation.

## Access and retrieval principles

- The authenticated or backend-controlled demo identity determines the user's country and authorized role; neither is inferred from the query language or trusted from arbitrary client input.
- Global documents are available to all employees; local documents are limited to the authorized country and audience.
- Managers may access manager-specific material for their country. HR access is scoped to its own country; there is no default global HR administrator.
- Employee-specific information is retrieved from authorized, read-only structured data sources, **not** embedded into the policy corpus.
- The initial demo uses fictional identities and backend-controlled sessions; it is not presented as production authentication.
- Retrieval, citations, traces, and debugging interfaces must not reveal unauthorized content.
- A question in Spanish can retrieve an authorized English policy, and vice versa. Language must not override country or access controls.

## Relationships to design while drafting

These are **planned scenarios**, not claims that the policy text already contains the corresponding rules:

| Documents / sources | Intended relationship |
| --- | --- |
| ES-001 + employee vacation records (SQL) | Combine the employee's remaining balance with current vacation rules |
| ES-001 + ES-002 | Distinguish vacation from other leave and absence categories |
| ES-002 + ES-006 | Distinguish employee-facing rules from manager-only operational procedures |
| ES-002 + ES-007 | Separate public leave guidance from restricted HR handling procedures |
| ES-003 + ES-005 | Clarify remote work versus business travel and reimbursement |
| GLB-002 + ES-003 | Apply global security requirements alongside local remote-work arrangements |
| ES-001 + MX-001 + EN-001 | Test country isolation and multilingual retrieval without mixing local entitlements |

## Versioning and metadata plan

Each ingested document should have a stable identity and sufficient metadata to enforce scope and determine whether its content is current:

- `document_id`
- `country` or global scope
- `language`
- `allowed_roles` / audience
- `version`
- `effective_from`
- `effective_to` (nullable)
- `status` (e.g. current, superseded, draft)

Exact metadata representation and storage schema will be decided during implementation. Superseded documents may be retained for explicit historical queries and versioning tests, but must not be treated as current evidence.

## Evaluation scenarios

| Scenario | Example question or condition | Expected behavior |
| --- | --- | --- |
| Direct retrieval | “¿Cuántos días de vacaciones me corresponden?” | Ground the answer in the applicable current policy |
| Multi-document | “¿Puedo teletrabajar durante un viaje de trabajo?” | Retrieve relevant authorized policies and reconcile their provisions |
| Policy + SQL | “¿Cuántos días me quedan y puedo usarlos en diciembre?” | Obtain the authorized balance from SQL and the applicable policy from RAG |
| Restricted document | Employee asks for internal HR exception-handling criteria | Do not disclose HR-only content |
| Document version | “¿Cuál es el límite actual de alojamiento?” | Use the effective version rather than a superseded one |
| Missing evidence | “¿La empresa paga una suscripción a Netflix?” | Abstain or clearly state that the available policies do not establish this |
| Cross-language retrieval | Spanish employee asks “What is my vacation entitlement?” | Retrieve the Spanish policy despite the English query |
| Cross-language retrieval | England employee asks “¿Cuál es mi política de vacaciones?” | Retrieve the authorized English policy despite the Spanish query |
| Country isolation | Mexico employee asks about vacation entitlement | Apply Mexico policy, not Spain policy merely because both are in Spanish |

These examples will inform future development, validation, and held-out test datasets. Final evaluation questions and expected answers should be grounded in the **actual drafted policies**, not invented in advance.

## Drafting and implementation sequence

1. Draft and review Spain's employee-facing policies, beginning with **ES-001 — Vacaciones y días libres**.
2. Add manager-only and HR-only policies with explicit access boundaries.
3. Add global policies and initial Mexico/England policies.
4. Create fictional employee records and balances consistent with the approved policies.
5. Build ingestion, baseline retrieval, authorization, and evaluation; evolve toward CRAG based on measured weaknesses.

## Corpus location

Actual source documents will be placed under `data/corpus/`, with geographic organization such as `global/`, `spain/`, `mexico/`, and `england/` created as needed. This inventory belongs under `docs/` and **must not be ingested as a policy**.
