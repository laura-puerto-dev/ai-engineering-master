# CRAG Evaluation Report

- Generated: 2026-11-25T16:20:27.546903+00:00
- Variant: crag
- Dataset: docs\evaluation\crag-validation-questions.yaml
- top_k: 10  ·  max_retrievals: 3

These automatic metrics describe technical execution, outcome (answered vs. abstained), route distribution, retrieval counts, latency, and structural validity. They never claim an answer is factually correct or that its evidence is actually sufficient — see the manual_review fields below and in the JSON results file for that. An answer being produced (not abstained) is not the same thing as that answer being correct.

## Summary table

| ID | Category | Expected | Got | Routes | Retrievals | Latency (s) | Citations | Incidents |
|---|---|---|---|---|---|---:|---|---|
| val-01 | direct_evidence | answerable | answerable | sufficient | 1 | 16.93 | 1 | - |
| val-02 | direct_evidence | answerable | answerable | sufficient | 1 | 13.30 | 1 | - |
| val-03 | direct_evidence | answerable | answerable | sufficient | 1 | 12.39 | 2 | - |
| val-04 | multi_fragment | answerable | answerable | sufficient | 1 | 18.65 | 2 | - |
| val-05 | multi_fragment | answerable | answerable | sufficient | 1 | 18.17 | 2 | - |
| val-06 | multi_fragment | answerable | answerable | sufficient | 1 | 18.07 | 4 | - |
| val-07 | partially_answerable | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 42.19 | 0 | - |
| val-08 | partially_answerable | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 50.13 | 0 | - |
| val-09 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 41.23 | 0 | - |
| val-10 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 35.65 | 0 | - |
| val-11 | access_restricted | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 55.21 | 0 | - |
| val-12 | access_restricted | abstain | abstain | insufficient -> ambiguous -> insufficient | 3 | 50.62 | 0 | - |

## Automatic metrics

```json
{
  "total_questions": 12,
  "technical_errors": {
    "count": 0,
    "ids": []
  },
  "executed_successfully": {
    "count": 12,
    "ids": [
      "val-01",
      "val-02",
      "val-03",
      "val-04",
      "val-05",
      "val-06",
      "val-07",
      "val-08",
      "val-09",
      "val-10",
      "val-11",
      "val-12"
    ]
  },
  "outcome": {
    "answerable_total": 6,
    "answerable_executed": 6,
    "answerable_technical_errors": 0,
    "answerable_answered": 6,
    "answerable_answered_rate": 1.0,
    "false_abstentions": 0,
    "false_abstention_ids": [],
    "abstain_total": 6,
    "abstain_executed": 6,
    "abstain_technical_errors": 0,
    "abstain_correct": 6,
    "abstain_correct_rate": 1.0,
    "false_answers": 0,
    "false_answer_ids": []
  },
  "routes": {
    "grader_route_counts": {
      "sufficient": 6,
      "ambiguous": 10,
      "insufficient": 8
    },
    "effective_route_counts": {
      "sufficient": 6,
      "ambiguous": 10,
      "insufficient": 8
    },
    "route_divergences": []
  },
  "retrievals": {
    "distribution": {
      "1": 6,
      "3": 6
    },
    "mean": 2,
    "questions_needing_reformulation": 6
  },
  "latency_seconds": {
    "mean": 31.044415408337954,
    "median": 27.152606150018983,
    "max": 55.21096009993926,
    "count": 12
  },
  "citations": {
    "total_citations_checked": 12,
    "citations_structurally_valid_rate": 1.0,
    "citations_from_final_context_rate": 1.0
  },
  "evidence_coverage": {
    "answerable_with_evidence": 6,
    "coverage_in_final_context_at_k": 1.0,
    "coverage_ever_retrieved_at_k": 1.0,
    "pct_all_found_in_final_context": 1.0
  }
}
```

## Per-question detail

### val-01 — spain-employee (expected: answerable)

**Question:** ¿Entre qué horas puede iniciar su jornada un empleado en España que tenga flexibilidad horaria, y qué franja horaria común de colaboración se aplica a todo el equipo?

**Expected answer summary:** La entrada puede realizarse entre las 08:00 y las 10:00; existe una franja común de colaboración de 10:00 a 14:00 para facilitar reuniones y coordinación.
**Expected aspects:** ['Ventana de entrada flexible (08:00-10:00)', 'Franja común de colaboración (10:00-14:00)']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Un empleado en España con flexibilidad horaria puede iniciar su jornada entre las 08:00 y las 10:00, siempre que sus funciones y su régimen individual lo permitan, respetando la duración de la jornada correspondiente. Además, se establece una franja común de colaboración de 10:00 a 14:00 para facilitar reuniones y coordinación entre los equipos. Esta franja no sustituye las reglas sobre jornada, pausas, descansos o disponibilidad acordada.

**Citations:**
- ES-003 v1.0 — 4. Flexibilidad horaria (`ES-003:1.0:4`)

**Attempt 1** — query: '¿Entre qué horas puede iniciar su jornada un empleado en España que tenga flexibilidad horaria, y qué franja horaria común de colaboración se aplica a todo el equipo?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-003:1.0:4 | 0.2507 | 0.9997 |
| ES-003:1.0:0 | 0.4292 | 0.9930 |
| ES-004:1.0:14 | 0.4211 | 0.9901 |
| ES-003:1.0:1 | 0.4210 | 0.9891 |
| GLB-002:1.0:7 | 0.4485 | 0.9605 |
| GLB-002:1.0:11 | 0.4358 | 0.9027 |
| ES-003:1.0:3 | 0.4678 | 0.0895 |
| ES-005:1.0:10 | 0.4588 | 0.0894 |
| ES-004:1.0:11 | 0.4225 | 0.0169 |
| ES-004:1.0:5 | 0.4146 | 0.0149 |

- kept: ['ES-003:1.0:4']
- discarded: ['ES-003:1.0:0', 'ES-004:1.0:14', 'ES-003:1.0:1', 'GLB-002:1.0:7', 'GLB-002:1.0:11', 'ES-003:1.0:3', 'ES-005:1.0:10', 'ES-004:1.0:11', 'ES-004:1.0:5']
- covered_aspects: ['horario de entrada flexible (08:00-10:00)', 'franja común de colaboración (10:00-14:00)']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [0] responde directamente y por completo ambas partes de la pregunta: el rango de entrada flexible y la franja común de colaboración.'

**Expected evidence:**
- ES-003:1.0:4: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-02 — mexico-employee (expected: answerable)

**Question:** ¿Cuántos días retribuidos por asuntos personales por año natural concede Northfern a los empleados elegibles de México, al margen de las vacaciones?

**Expected answer summary:** 1 día retribuido por año natural, independiente de las vacaciones y no acumulable al año siguiente.
**Expected aspects:** ['Cantidad: 1 día por año natural', 'Independencia respecto al saldo de vacaciones']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Northfern concede 1 día retribuido por asuntos personales por año natural a los empleados elegibles de México, independiente de las vacaciones y de los permisos legalmente exigibles.

**Citations:**
- MX-001 v1.1 — 8. Día de asuntos personales (`MX-001:1.1:11`)

**Attempt 1** — query: '¿Cuántos días retribuidos por asuntos personales por año natural concede Northfern a los empleados elegibles de México, al margen de las vacaciones?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2035 | 1.0000 |
| MX-001:1.1:3 | 0.3766 | 0.9914 |
| MX-001:1.1:0 | 0.3294 | 0.9850 |
| MX-001:1.1:1 | 0.3434 | 0.9769 |
| MX-002:1.0:0 | 0.3850 | 0.9520 |
| GLB-001:1.0:5 | 0.4464 | 0.8523 |
| GLB-001:1.0:8 | 0.4480 | 0.8261 |
| MX-002:1.0:1 | 0.3974 | 0.3504 |
| GLB-001:1.0:12 | 0.4658 | 0.2009 |
| GLB-002:1.0:4 | 0.4551 | 0.0360 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:3', 'MX-001:1.1:0', 'MX-001:1.1:1', 'MX-002:1.0:0', 'GLB-001:1.0:5', 'GLB-001:1.0:8', 'MX-002:1.0:1', 'GLB-001:1.0:12', 'GLB-002:1.0:4']
- covered_aspects: ['number of paid personal day(s) granted per calendar year in Mexico', 'independence from vacation days']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragment [0] directly states Northfern grants 1 paid personal day per calendar year to eligible Mexico employees, separate from vacation, fully answering the question.'

**Expected evidence:**
- MX-001:1.1:11: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-03 — england-employee (expected: answerable)

**Question:** Roughly how many bank/public holidays does Northfern's typical annual calendar include for employees in England, in addition to the 25 days of annual leave?

**Expected answer summary:** Around 8 bank/public holidays in a typical year, on top of and never deducted from the 25-day annual leave entitlement — though the exact number and dates must be checked against the published calendar for the relevant year.
**Expected aspects:** ['Approximate count (around 8) with the caveat that the exact number varies by year', 'Bank holidays are additional to, never deducted from, the 25-day entitlement']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Northfern's typical annual calendar for England includes around 8 bank/public holidays, which are in addition to the 25 working days of paid annual leave and are not deducted from that entitlement. However, the exact number and dates can vary by year, so employees should check the published company holiday calendar for the relevant year.

**Citations:**
- EN-001 v1.0 — 10. Bank holidays and operational requirements (`EN-001:1.0:10`)
- EN-001 v1.0 — 2. Holiday year and annual entitlement (`EN-001:1.0:2`)

**Attempt 1** — query: "Roughly how many bank/public holidays does Northfern's typical annual calendar include for employees in England, in addition to the 25 days of annual leave?"

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:10 | 0.3823 | 0.9998 |
| EN-001:1.0:2 | 0.3647 | 0.9997 |
| EN-001:1.0:7 | 0.3117 | 0.9985 |
| EN-001:1.0:1 | 0.5048 | 0.9969 |
| EN-001:1.0:5 | 0.4981 | 0.9944 |
| EN-001:1.0:0 | 0.3955 | 0.9804 |
| GLB-001:1.0:1 | 0.5192 | 0.1239 |
| GLB-001:1.0:8 | 0.5259 | 0.0111 |
| GLB-001:1.0:5 | 0.5054 | 0.0106 |
| GLB-002:1.0:4 | 0.5310 | 0.0060 |

- kept: ['EN-001:1.0:10', 'EN-001:1.0:2']
- discarded: ['EN-001:1.0:7', 'EN-001:1.0:1', 'EN-001:1.0:5', 'EN-001:1.0:0', 'GLB-001:1.0:1', 'GLB-001:1.0:8', 'GLB-001:1.0:5', 'GLB-002:1.0:4']
- covered_aspects: ['typical number of bank/public holidays in England calendar', 'confirmation these are in addition to 25 days annual leave']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragments 0 and 1 both state the typical calendar includes around 8 bank holidays, separate from and in addition to the 25-day annual leave entitlement, fully answering the question.'

**Expected evidence:**
- EN-001:1.0:10: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-04 — spain-employee (expected: answerable)

**Question:** ¿Qué tipo de funciones hacen que un puesto sea elegible para el régimen ordinario de teletrabajo en España, y qué importe máximo de ayuda de equipamiento de teletrabajo puede solicitar un empleado con un puesto elegible?

**Expected answer summary:** Son elegibles los puestos cuyas funciones pueden desarrollarse a distancia sin afectar a requisitos operativos, de atención presencial o de seguridad (ES-003 §2) — no por pertenecer a un departamento concreto, y pudiendo matizarse por condiciones individuales formalizadas; un empleado con un puesto elegible puede solicitar hasta 300 € de ayuda de equipamiento por periodo de tres años (ES-004 §8).
**Expected aspects:** ['Criterio positivo de elegibilidad: funciones que pueden desarrollarse a distancia sin afectar a requisitos operativos, de atención presencial o de seguridad', 'Pueden aplicar condiciones individuales formalizadas adicionales', 'Importe máximo de la ayuda de equipamiento: 300 € por periodo de 3 años']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Según ES-003, el régimen ordinario de teletrabajo se ofrece a los puestos cuyas funciones pueden desarrollarse a distancia sin afectar a requisitos operativos, de atención presencial o de seguridad; la elegibilidad se determina según las funciones del puesto y las condiciones individuales aplicables, no por pertenecer a un departamento concreto. En cuanto a la ayuda de equipamiento, según ES-004, las personas con puestos elegibles para teletrabajo pueden solicitar una ayuda de hasta 300 € por periodo de tres años para equipamiento autorizado, aunque este límite no se renueva cada año y no se acumulan los importes no utilizados entre periodos.

**Citations:**
- ES-004 v1.0 — 8. Ayuda para equipamiento de teletrabajo (`ES-004:1.0:9`)
- ES-003 v1.0 — 2. Ámbito y elegibilidad (`ES-003:1.0:2`)

**Attempt 1** — query: '¿Qué tipo de funciones hacen que un puesto sea elegible para el régimen ordinario de teletrabajo en España, y qué importe máximo de ayuda de equipamiento de teletrabajo puede solicitar un empleado con un puesto elegible?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:9 | 0.2466 | 0.9999 |
| ES-003:1.0:2 | 0.2878 | 0.9994 |
| ES-004:1.0:14 | 0.4192 | 0.9990 |
| ES-003:1.0:3 | 0.3475 | 0.9980 |
| ES-003:1.0:12 | 0.3996 | 0.9872 |
| GLB-002:1.0:7 | 0.4233 | 0.8289 |
| ES-003:1.0:5 | 0.4190 | 0.3020 |
| ES-005:1.0:12 | 0.4293 | 0.2333 |
| ES-003:1.0:7 | 0.4156 | 0.1055 |
| ES-005:1.0:10 | 0.4101 | 0.1005 |

- kept: ['ES-003:1.0:2', 'ES-004:1.0:9']
- discarded: ['ES-004:1.0:14', 'ES-003:1.0:3', 'ES-003:1.0:12', 'GLB-002:1.0:7', 'ES-003:1.0:5', 'ES-005:1.0:12', 'ES-003:1.0:7', 'ES-005:1.0:10']
- covered_aspects: ['criterios de funciones que determinan elegibilidad para teletrabajo ordinario (funciones que pueden desarrollarse a distancia sin afectar requisitos operativos, de atención presencial o de seguridad)', 'importe máximo de ayuda de equipamiento de teletrabajo (hasta 300€ por periodo de tres años)']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [1] detalla los criterios de elegibilidad por funciones del puesto y el fragmento [0] indica el importe máximo de 300€ por periodo de tres años, cubriendo ambos aspectos de la pregunta.'

**Expected evidence:**
- ES-003:1.0:2: ever_retrieved=True in_final_context=True
- ES-004:1.0:9: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-05 — spain-manager (expected: answerable)

**Question:** Como manager en España, si apruebo que uno de mis colaboradores se inscriba en un congreso profesional, ¿eso implica que también he aprobado su viaje y sus gastos de desplazamiento?

**Expected answer summary:** No. La aprobación de la inscripción a un evento no implica por sí sola la aprobación de un viaje ni la cobertura ilimitada de sus gastos (ES-004 §6); el viaje profesional requiere su propia aprobación previa del responsable directo, indicando motivo de negocio, destino, fechas previstas y una estimación razonable del coste (ES-005 §3), y los desplazamientos, alojamientos y dietas se rigen por ES-005.
**Expected aspects:** ['La aprobación de la inscripción a un evento no equivale a aprobar el viaje ni sus gastos', 'El viaje profesional requiere su propia aprobación previa, con motivo de negocio, destino, fechas y estimación de coste']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** No. Según la política ES-004, la aprobación de la inscripción a un evento no implica por sí sola la aprobación de un viaje ni la cobertura ilimitada de sus gastos. Además, los desplazamientos, alojamientos, dietas y reembolsos se rigen por la política ES-005, que exige sus propias autorizaciones. De hecho, ES-005 establece que todo viaje profesional requiere aprobación previa del responsable directo, indicando motivo de negocio, destino, fechas y una estimación razonable del coste, y que si se prevé superar los límites de gasto establecidos, es necesaria una autorización excepcional previa adicional.

**Citations:**
- ES-005 v1.0 — 3. Autorización y planificación del viaje (`ES-005:1.0:3`)
- ES-004 v1.0 — 6. Conferencias, congresos y eventos profesionales (`ES-004:1.0:7`)

**Attempt 1** — query: 'Como manager en España, si apruebo que uno de mis colaboradores se inscriba en un congreso profesional, ¿eso implica que también he aprobado su viaje y sus gastos de desplazamiento?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:3 | 0.3676 | 0.9998 |
| ES-004:1.0:7 | 0.3382 | 0.9998 |
| ES-005:1.0:2 | 0.3818 | 0.9995 |
| ES-005:1.0:9 | 0.4247 | 0.9979 |
| ES-005:1.0:6 | 0.3974 | 0.9978 |
| ES-005:1.0:1 | 0.4103 | 0.9975 |
| ES-005:1.0:10 | 0.4142 | 0.9974 |
| ES-005:1.0:8 | 0.4264 | 0.9906 |
| ES-005:1.0:7 | 0.4209 | 0.9695 |
| ES-006:1.0:2 | 0.4027 | 0.3887 |

- kept: ['ES-004:1.0:7', 'ES-005:1.0:3']
- discarded: ['ES-005:1.0:2', 'ES-005:1.0:9', 'ES-005:1.0:6', 'ES-005:1.0:1', 'ES-005:1.0:10', 'ES-005:1.0:8', 'ES-005:1.0:7', 'ES-006:1.0:2']
- covered_aspects: ['La aprobación de inscripción a un evento/congreso no implica aprobación automática del viaje', 'Los gastos de desplazamiento, alojamiento y dietas se rigen por ES-005 y requieren sus propias autorizaciones', 'Necesidad de aprobación previa del responsable directo para el viaje en sí, con indicación de motivo, destino, fechas y coste estimado']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [1] responde directamente que la aprobación de inscripción a un evento no implica aprobación del viaje ni de sus gastos, y remite a ES-005 para estos; el fragmento [0] confirma que el viaje requiere aprobación previa separada, cubriendo completamente la pregunta.'

**Expected evidence:**
- ES-004:1.0:7: ever_retrieved=True in_final_context=True
- ES-005:1.0:3: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-06 — spain-manager (expected: answerable)

**Question:** Como manager en España, ¿qué tipo de información sobre las ausencias de mis colaboradores directos puedo consultar, y qué tengo explícitamente prohibido consultar?

**Expected answer summary:** Puedo consultar los datos administrativos necesarios de mis subordinados directos (fechas de ausencias aprobadas, tipo administrativo, estado de la solicitud). Tengo prohibido acceder a registros de otros equipos por el mero hecho de ser manager, y no puedo consultar diagnósticos médicos, informes clínicos ni justificantes sensibles.
**Expected aspects:** ['Alcance permitido: datos administrativos de subordinados directos (fechas, tipo, estado)', 'Límite explícito: no otros equipos, no información médica/clínica confidencial']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Como manager en España, puedes consultar la información administrativa autorizada de tus subordinados directos que sea necesaria para tus funciones, como: fechas de ausencias aprobadas, el tipo administrativo de ausencia y el estado de una solicitud [2]. Este acceso se basa en el principio de acceso mínimo necesario y se limita exclusivamente a tus colaboradores directos [0][1][2].

Tienes explícitamente prohibido:
- Acceder a registros de empleados de otros equipos por el mero hecho de ser manager [2].
- Consultar diagnósticos médicos, documentación clínica o justificantes sensibles [2][3].
- Acceder a información de otros países o a información médica confidencial, ya que la condición de manager no concede ese acceso [0][1].
- Pedir diagnósticos, informes clínicos o explicaciones médicas detalladas cuando se comunique una ausencia imprevista [3].
- Compartir la información personal en chats de equipo, documentos públicos o canales no autorizados [2][3].

Además, los justificantes y documentos sensibles deben gestionarse exclusivamente mediante los canales autorizados de RR. HH., y no deben adjuntarse al chat de Policy Consultant ni compartirse con personas que no necesiten acceder a ellos [1][3].

**Citations:**
- ES-006 v1.0 — 2. Alcance y acceso (`ES-006:1.0:2`)
- ES-002 v1.0 — 10. Privacidad y justificantes (`ES-002:1.0:10`)
- ES-006 v1.0 — 9. Acceso a información del equipo y confidencialidad (`ES-006:1.0:9`)
- ES-006 v1.0 — 6. Ausencias imprevistas y enfermedad (`ES-006:1.0:6`)

**Attempt 1** — query: 'Como manager en España, ¿qué tipo de información sobre las ausencias de mis colaboradores directos puedo consultar, y qué tengo explícitamente prohibido consultar?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-006:1.0:2 | 0.2390 | 0.9998 |
| ES-002:1.0:10 | 0.3467 | 0.9996 |
| ES-006:1.0:9 | 0.3019 | 0.9995 |
| ES-003:1.0:12 | 0.4143 | 0.9988 |
| ES-002:1.0:11 | 0.3569 | 0.9979 |
| ES-006:1.0:6 | 0.3661 | 0.9968 |
| ES-006:1.0:3 | 0.4101 | 0.9876 |
| ES-006:1.0:8 | 0.4092 | 0.9507 |
| ES-001:1.0:9 | 0.4108 | 0.8658 |
| ES-006:1.0:5 | 0.4152 | 0.1858 |

- kept: ['ES-002:1.0:10', 'ES-006:1.0:2', 'ES-006:1.0:6', 'ES-006:1.0:9']
- discarded: ['ES-003:1.0:12', 'ES-002:1.0:11', 'ES-006:1.0:3', 'ES-006:1.0:8', 'ES-001:1.0:9', 'ES-006:1.0:5']
- covered_aspects: ['qué información administrativa puede consultar un manager sobre subordinados directos (fechas de ausencias aprobadas, tipo administrativo, estado de solicitud)', 'límites de acceso a otros equipos u otros países', 'prohibición de acceder a información médica confidencial, diagnósticos, informes clínicos o justificantes sensibles', 'principio de acceso mínimo necesario', 'canales autorizados para justificantes sensibles']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Los fragmentos ES-006 y ES-002 cubren de forma explícita y coherente tanto lo que un manager puede consultar (datos administrativos de ausencias de subordinados directos) como lo que tiene prohibido (datos médicos, de otros equipos, justificantes sensibles), respondiendo completamente a la pregunta.'

**Expected evidence:**
- ES-006:1.0:9: ever_retrieved=True in_final_context=True
- ES-002:1.0:10: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-07 — mexico-employee (expected: abstain)

**Question:** Llevo tres años y medio trabajando en Northfern México. ¿Cuántos días de asuntos personales me corresponden por año natural, y cuántos me quedan disponibles este año en concreto?

**Expected answer summary:** —
**Expected aspects:** ['Cubierto en el corpus: cuantía anual general del beneficio (1 día por año natural, independiente de vacaciones)', 'No cubierto: disponibilidad/saldo personal restante de esta persona en este momento']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Llevo tres años y medio trabajando en Northfern México. ¿Cuántos días de asuntos personales me corresponden por año natural, y cuántos me quedan disponibles este año en concreto?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2181 | 0.9998 |
| MX-001:1.1:3 | 0.4045 | 0.9931 |
| MX-001:1.1:1 | 0.3433 | 0.9834 |
| MX-001:1.1:0 | 0.3418 | 0.9826 |
| MX-002:1.0:0 | 0.3892 | 0.9667 |
| GLB-001:1.0:5 | 0.4244 | 0.6397 |
| GLB-001:1.0:1 | 0.4451 | 0.5955 |
| GLB-001:1.0:8 | 0.4431 | 0.5940 |
| GLB-002:1.0:4 | 0.4352 | 0.3347 |
| MX-002:1.0:1 | 0.3900 | 0.0663 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:3', 'MX-001:1.1:1', 'MX-001:1.1:0', 'MX-002:1.0:0', 'GLB-001:1.0:5', 'GLB-001:1.0:1', 'GLB-001:1.0:8', 'GLB-002:1.0:4', 'MX-002:1.0:1']
- covered_aspects: ['Número de días de asuntos personales por año natural (1 día)']
- missing_aspects: ['Días de asuntos personales ya utilizados o disponibles para este empleado en concreto este año (debe consultarse en el sistema de personal, no está en esta política)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento 0 establece claramente el derecho a 1 día de asuntos personales por año, pero indica explícitamente que la disponibilidad individual se consulta en el sistema de personal, no en la política, dejando sin responder cuántos días le quedan a este empleado concreto.'

**Attempt 2** — query: 'Política de días de asuntos personales por año natural Northfern México: cantidad de días asignados según antigüedad'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2618 | 0.9998 |
| MX-001:1.1:5 | 0.4469 | 0.9980 |
| MX-001:1.1:1 | 0.3898 | 0.9902 |
| MX-001:1.1:3 | 0.3344 | 0.9873 |
| MX-001:1.1:4 | 0.4740 | 0.9633 |
| MX-001:1.1:0 | 0.3763 | 0.9540 |
| MX-002:1.0:0 | 0.4511 | 0.7521 |
| GLB-001:1.0:5 | 0.4829 | 0.4048 |
| MX-001:1.1:10 | 0.4768 | 0.3739 |
| MX-002:1.0:1 | 0.4450 | 0.3489 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:5', 'MX-001:1.1:1', 'MX-001:1.1:3', 'MX-001:1.1:4', 'MX-001:1.1:0', 'MX-002:1.0:0', 'GLB-001:1.0:5', 'MX-001:1.1:10', 'MX-002:1.0:1']
- covered_aspects: ['Número de días de asuntos personales por año natural (1 día)']
- missing_aspects: ['Saldo disponible/restante de días de asuntos personales para el empleado en el año en curso']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento [0] establece el derecho a 1 día de asuntos personales por año natural, pero indica explícitamente que la disponibilidad individual debe consultarse en el sistema de personal, no en la política, por lo que falta el dato del saldo concreto para este año.'

**Attempt 3** — query: 'Consulta de saldo disponible y días restantes de asuntos personales en el año en curso para empleados Northfern México'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2981 | 0.9994 |
| MX-001:1.1:6 | 0.3917 | 0.9975 |
| MX-001:1.1:1 | 0.3486 | 0.9601 |
| MX-001:1.1:3 | 0.4011 | 0.9315 |
| MX-002:1.0:0 | 0.3767 | 0.9161 |
| MX-001:1.1:0 | 0.3630 | 0.9083 |
| GLB-002:1.0:4 | 0.4358 | 0.5956 |
| GLB-001:1.0:0 | 0.4238 | 0.5840 |
| GLB-001:1.0:5 | 0.4188 | 0.2766 |
| MX-002:1.0:1 | 0.3937 | 0.1662 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:6', 'MX-001:1.1:1', 'MX-001:1.1:3', 'MX-002:1.0:0', 'MX-001:1.1:0', 'GLB-002:1.0:4', 'GLB-001:1.0:0', 'GLB-001:1.0:5', 'MX-002:1.0:1']
- covered_aspects: ['General entitlement of 1 paid personal day per calendar year for eligible employees in Mexico']
- missing_aspects: ['Individual remaining/available personal days for this specific employee this year, which requires checking the personnel system']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Fragment 0 establishes the general rule of 1 personal day per year but explicitly states individual availability must be checked in the personnel system, so the specific remaining balance for this employee is not answered.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-08 — spain-hr (expected: abstain)

**Question:** Estoy revisando el expediente de una excepción de vacaciones de más de 15 días laborables consecutivos para Marta, una empleada de España. ¿Qué información debe recoger el expediente sobre el periodo solicitado y el saldo disponible, y cuál es el saldo de vacaciones disponible actualmente para Marta?

**Expected answer summary:** —
**Expected aspects:** ['Cubierto en el corpus: qué debe recoger el expediente (periodo solicitado y saldo disponible, verificado en el sistema de personal)', 'No cubierto: el saldo de vacaciones real de Marta en este momento']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Estoy revisando el expediente de una excepción de vacaciones de más de 15 días laborables consecutivos para Marta, una empleada de España. ¿Qué información debe recoger el expediente sobre el periodo solicitado y el saldo disponible, y cuál es el saldo de vacaciones disponible actualmente para Marta?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-007:1.0:4 | 0.3551 | 0.9982 |
| ES-001:1.0:3 | 0.3353 | 0.9976 |
| ES-006:1.0:4 | 0.3141 | 0.9922 |
| ES-001:1.0:8 | 0.3155 | 0.9900 |
| ES-001:1.0:4 | 0.3344 | 0.9848 |
| ES-001:1.0:6 | 0.2913 | 0.9841 |
| ES-002:1.0:11 | 0.3790 | 0.9838 |
| ES-001:1.0:9 | 0.3349 | 0.9681 |
| ES-001:1.0:7 | 0.3705 | 0.9612 |
| ES-006:1.0:8 | 0.3670 | 0.6828 |

- kept: ['ES-007:1.0:4']
- discarded: ['ES-001:1.0:3', 'ES-006:1.0:4', 'ES-001:1.0:8', 'ES-001:1.0:4', 'ES-001:1.0:6', 'ES-002:1.0:11', 'ES-001:1.0:9', 'ES-001:1.0:7', 'ES-006:1.0:8']
- covered_aspects: ['What the exception file must record regarding requested period and available balance (per ES-007)', 'General process for handling exceptions over 15 consecutive working days']
- missing_aspects: ["Marta's actual current vacation balance, which must be looked up in the personnel management system, not available in these policy documents"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "ES-007 clearly specifies what the exception record must include about period and balance, but no fragment provides Marta's actual personal balance, which requires checking the personnel system rather than policy text."

**Attempt 2** — query: 'Requisitos de documentación para excepción de vacaciones de más de 15 días laborables consecutivos en España: periodo solicitado y saldo de vacaciones disponible'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:8 | 0.3157 | 0.9996 |
| ES-007:1.0:4 | 0.3696 | 0.9993 |
| ES-001:1.0:4 | 0.3089 | 0.9992 |
| ES-006:1.0:4 | 0.3220 | 0.9980 |
| ES-001:1.0:6 | 0.2628 | 0.9971 |
| ES-002:1.0:11 | 0.3869 | 0.9902 |
| ES-006:1.0:8 | 0.3750 | 0.9898 |
| ES-001:1.0:7 | 0.3856 | 0.9855 |
| ES-001:1.0:3 | 0.3913 | 0.8719 |
| ES-005:1.0:8 | 0.4068 | 0.6842 |

- kept: ['ES-007:1.0:4']
- discarded: ['ES-001:1.0:8', 'ES-001:1.0:4', 'ES-006:1.0:4', 'ES-001:1.0:6', 'ES-002:1.0:11', 'ES-006:1.0:8', 'ES-001:1.0:7', 'ES-001:1.0:3', 'ES-005:1.0:8']
- covered_aspects: ['Requisitos del expediente sobre periodo solicitado y saldo disponible (verificación en sistema de personal, motivo, valoración del responsable, propuesta de resolución)']
- missing_aspects: ['Saldo de vacaciones disponible actualmente para Marta (dato individual no incluido en estas políticas, requiere consulta al sistema de personal)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento ES-007 responde claramente a qué debe recoger el expediente sobre periodo y saldo, pero ningún fragmento contiene el saldo real de Marta, que debe consultarse en el sistema de personal, por lo que la pregunta no queda totalmente resuelta.'

**Attempt 3** — query: 'Consulta de saldo de días de vacaciones disponibles para empleado individual en sistema de personal de Recursos Humanos España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:3 | 0.3386 | 0.9993 |
| ES-001:1.0:9 | 0.3082 | 0.9989 |
| ES-002:1.0:4 | 0.3955 | 0.9988 |
| ES-001:1.0:7 | 0.3871 | 0.9978 |
| ES-006:1.0:4 | 0.3600 | 0.9930 |
| ES-002:1.0:11 | 0.3558 | 0.9899 |
| ES-003:1.0:12 | 0.4100 | 0.9803 |
| ES-001:1.0:8 | 0.3783 | 0.9502 |
| ES-006:1.0:11 | 0.4073 | 0.8488 |
| ES-006:1.0:8 | 0.4019 | 0.5923 |

- kept: ['ES-007:1.0:4']
- discarded: ['ES-001:1.0:3', 'ES-001:1.0:9', 'ES-002:1.0:4', 'ES-001:1.0:7', 'ES-006:1.0:4', 'ES-002:1.0:11', 'ES-003:1.0:12', 'ES-001:1.0:8', 'ES-006:1.0:11', 'ES-006:1.0:8']
- covered_aspects: ['What the exception dossier must include regarding requested period and available balance (verified in personnel system)', 'General process for exceptions over 15 consecutive working days']
- missing_aspects: ["Marta's actual current vacation balance (individual record lookup required, not available in policy text)"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment [0] clearly answers what the dossier must document about period and balance, but no fragment contains Marta's specific, individual vacation balance, which must be checked in the personnel system."

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-09 — spain-employee (expected: abstain)

**Question:** ¿Northfern Technologies ofrece algún programa de coche de empresa o ayuda de leasing de vehículo a sus empleados en España?

**Expected answer summary:** —
**Expected aspects:** —

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: '¿Northfern Technologies ofrece algún programa de coche de empresa o ayuda de leasing de vehículo a sus empleados en España?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:1 | 0.3770 | 0.9956 |
| ES-004:1.0:2 | 0.3819 | 0.9834 |
| ES-001:1.0:2 | 0.3408 | 0.9469 |
| ES-004:1.0:0 | 0.3562 | 0.9291 |
| ES-001:1.0:1 | 0.3706 | 0.9253 |
| ES-002:1.0:0 | 0.3780 | 0.9210 |
| ES-001:1.0:0 | 0.3495 | 0.8047 |
| ES-005:1.0:2 | 0.3624 | 0.7995 |
| ES-002:1.0:1 | 0.3815 | 0.7240 |
| ES-005:1.0:0 | 0.3663 | 0.6963 |

- kept: []
- discarded: ['ES-004:1.0:1', 'ES-004:1.0:2', 'ES-001:1.0:2', 'ES-004:1.0:0', 'ES-001:1.0:1', 'ES-002:1.0:0', 'ES-001:1.0:0', 'ES-005:1.0:2', 'ES-002:1.0:1', 'ES-005:1.0:0']
- covered_aspects: []
- missing_aspects: ['Existencia de programa de coche de empresa o leasing de vehículo para empleados en España']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona programas de coche de empresa o leasing de vehículos; tratan de vacaciones, permisos, viajes y formación/beneficios generales sin referencia a vehículos.'

**Attempt 2** — query: 'Política de beneficios para empleados en España: coche de empresa, leasing de vehículo o ayuda de transporte'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:11 | 0.4216 | 0.9934 |
| ES-004:1.0:2 | 0.3871 | 0.9880 |
| ES-004:1.0:14 | 0.3643 | 0.9796 |
| ES-004:1.0:1 | 0.4073 | 0.9728 |
| ES-002:1.0:4 | 0.4283 | 0.9652 |
| GLB-002:1.0:11 | 0.4119 | 0.9171 |
| ES-005:1.0:1 | 0.3780 | 0.4364 |
| ES-001:1.0:2 | 0.4279 | 0.3007 |
| ES-005:1.0:12 | 0.4245 | 0.0497 |
| ES-002:1.0:8 | 0.4264 | 0.0446 |

- kept: []
- discarded: ['ES-004:1.0:11', 'ES-004:1.0:2', 'ES-004:1.0:14', 'ES-004:1.0:1', 'ES-002:1.0:4', 'GLB-002:1.0:11', 'ES-005:1.0:1', 'ES-001:1.0:2', 'ES-005:1.0:12', 'ES-002:1.0:8']
- covered_aspects: []
- missing_aspects: ['Existencia de programa de coche de empresa o leasing de vehículo para empleados en España']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos recuperados menciona programas de coche de empresa o ayuda de leasing de vehículo; tratan de bienestar, formación, permisos, viajes y seguridad de la información, sin relación con la pregunta.'

**Attempt 3** — query: 'Beneficio de vehículo de empresa o auto asignado para empleados de Northfern Technologies en España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:1 | 0.3250 | 0.9991 |
| ES-002:1.0:4 | 0.3321 | 0.9980 |
| ES-004:1.0:2 | 0.3382 | 0.9953 |
| ES-005:1.0:2 | 0.3354 | 0.9934 |
| ES-004:1.0:0 | 0.2997 | 0.9884 |
| ES-001:1.0:2 | 0.3187 | 0.9855 |
| ES-005:1.0:0 | 0.3535 | 0.9794 |
| ES-001:1.0:1 | 0.3491 | 0.9783 |
| ES-002:1.0:0 | 0.3491 | 0.9457 |
| ES-001:1.0:0 | 0.3191 | 0.8376 |

- kept: []
- discarded: ['ES-004:1.0:1', 'ES-002:1.0:4', 'ES-004:1.0:2', 'ES-005:1.0:2', 'ES-004:1.0:0', 'ES-001:1.0:2', 'ES-005:1.0:0', 'ES-001:1.0:1', 'ES-002:1.0:0', 'ES-001:1.0:0']
- covered_aspects: []
- missing_aspects: ['existencia de programa de coche de empresa o ayuda de leasing de vehículo en España']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona programas de coche de empresa o leasing de vehículos; solo tratan formación, permisos, vacaciones y viajes profesionales, sin referencia a este beneficio específico.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-10 — england-employee (expected: abstain)

**Question:** Does Northfern Technologies provide any relocation assistance package for employees moving internationally between its England, Spain, or Mexico offices?

**Expected answer summary:** —
**Expected aspects:** —

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** Not enough evidence was found to answer with confidence.

**Citations:** none

**Attempt 1** — query: 'Does Northfern Technologies provide any relocation assistance package for employees moving internationally between its England, Spain, or Mexico offices?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| GLB-001:1.0:1 | 0.3646 | 0.8167 |
| GLB-001:1.0:12 | 0.3297 | 0.7521 |
| GLB-001:1.0:0 | 0.4629 | 0.6682 |
| GLB-002:1.0:1 | 0.4393 | 0.4629 |
| EN-001:1.0:0 | 0.4242 | 0.3609 |
| GLB-002:1.0:0 | 0.4396 | 0.2657 |
| GLB-002:1.0:5 | 0.4712 | 0.0907 |
| GLB-001:1.0:5 | 0.4472 | 0.0431 |
| EN-001:1.0:7 | 0.4083 | 0.0183 |
| GLB-002:1.0:4 | 0.4374 | 0.0111 |

- kept: []
- discarded: ['GLB-001:1.0:1', 'GLB-001:1.0:12', 'GLB-001:1.0:0', 'GLB-002:1.0:1', 'EN-001:1.0:0', 'GLB-002:1.0:0', 'GLB-002:1.0:5', 'GLB-001:1.0:5', 'EN-001:1.0:7', 'GLB-002:1.0:4']
- covered_aspects: []
- missing_aspects: ['Existence of relocation assistance policy', 'Details of relocation package for international moves between England, Spain, Mexico offices']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance or international transfer benefits; they cover code of conduct, confidentiality, leave, and security policies which are unrelated to the question.'

**Attempt 2** — query: 'international relocation assistance policy benefits England Spain Mexico office transfer'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:12 | 0.4575 | 0.9530 |
| GLB-001:1.0:12 | 0.4626 | 0.8453 |
| GLB-001:1.0:1 | 0.5320 | 0.8277 |
| GLB-002:1.0:11 | 0.5290 | 0.7575 |
| EN-001:1.0:1 | 0.4695 | 0.4125 |
| EN-001:1.0:0 | 0.5634 | 0.1503 |
| GLB-002:1.0:0 | 0.5696 | 0.1083 |
| GLB-002:1.0:7 | 0.4867 | 0.0484 |
| EN-001:1.0:9 | 0.5674 | 0.0143 |
| EN-001:1.0:7 | 0.5723 | 0.0035 |

- kept: []
- discarded: ['EN-001:1.0:12', 'GLB-001:1.0:12', 'GLB-001:1.0:1', 'GLB-002:1.0:11', 'EN-001:1.0:1', 'EN-001:1.0:0', 'GLB-002:1.0:0', 'GLB-002:1.0:7', 'EN-001:1.0:9', 'EN-001:1.0:7']
- covered_aspects: []
- missing_aspects: ['existence of a relocation assistance policy or package', 'terms for international relocation between England, Spain, Mexico offices']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance; they cover leave, code of conduct, and information security policies only.'

**Attempt 3** — query: 'employee relocation benefits policy for transfers between countries UK Spain Mexico office locations'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:12 | 0.4191 | 0.8949 |
| GLB-002:1.0:11 | 0.4400 | 0.8564 |
| EN-001:1.0:1 | 0.3974 | 0.5981 |
| GLB-001:1.0:1 | 0.4608 | 0.5030 |
| GLB-001:1.0:12 | 0.3989 | 0.3522 |
| GLB-002:1.0:0 | 0.5180 | 0.0741 |
| GLB-002:1.0:7 | 0.3848 | 0.0639 |
| GLB-002:1.0:1 | 0.5074 | 0.0125 |
| GLB-002:1.0:5 | 0.5229 | 0.0049 |
| EN-001:1.0:10 | 0.5214 | 0.0042 |

- kept: []
- discarded: ['EN-001:1.0:12', 'GLB-002:1.0:11', 'EN-001:1.0:1', 'GLB-001:1.0:1', 'GLB-001:1.0:12', 'GLB-002:1.0:0', 'GLB-002:1.0:7', 'GLB-002:1.0:1', 'GLB-002:1.0:5', 'EN-001:1.0:10']
- covered_aspects: []
- missing_aspects: ['existence of relocation assistance policy or package', 'eligibility and terms for international relocation between England, Spain, Mexico offices']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance; they cover leave, security, and code of conduct topics unrelated to relocation packages.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-11 — spain-employee (expected: abstain)

**Question:** ¿Qué procedimiento sigue RR. HH. para revisar una solicitud de formación que supere el presupuesto ordinario de 1.200 € anuales en España?

**Expected answer summary:** —
**Expected aspects:** ['Existe un procedimiento real descrito en ES-007 §7 (verificación de elegibilidad, finalidad profesional, presupuesto disponible y aprobaciones), pero no es accesible para este perfil']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: '¿Qué procedimiento sigue RR. HH. para revisar una solicitud de formación que supere el presupuesto ordinario de 1.200 € anuales en España?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:12 | 0.4594 | 0.9994 |
| ES-004:1.0:6 | 0.4302 | 0.9990 |
| ES-004:1.0:5 | 0.3853 | 0.9967 |
| ES-004:1.0:3 | 0.3852 | 0.9902 |
| ES-001:1.0:8 | 0.4974 | 0.9856 |
| ES-002:1.0:11 | 0.4952 | 0.8882 |
| ES-004:1.0:14 | 0.4804 | 0.8819 |
| ES-002:1.0:12 | 0.4819 | 0.8779 |
| ES-004:1.0:13 | 0.4947 | 0.3357 |
| ES-005:1.0:6 | 0.5049 | 0.0007 |

- kept: ['ES-004:1.0:12', 'ES-004:1.0:3', 'ES-004:1.0:6']
- discarded: ['ES-004:1.0:5', 'ES-001:1.0:8', 'ES-002:1.0:11', 'ES-004:1.0:14', 'ES-002:1.0:12', 'ES-004:1.0:13', 'ES-005:1.0:6']
- covered_aspects: ['General rule that excess budget requests require prior exceptional approval', "Approval granted for one case doesn't set precedent for others", 'Request must be made before committing expense', 'Who can be involved (direct manager, HR, administrative areas)']
- missing_aspects: ['Specific internal procedure/steps HR follows to evaluate exceptional training budget requests', 'Reference to the restricted internal procedures document (e.g., ES-007) detailing the review process']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "The fragments establish that excess budget requests need prior exceptional evaluation per 'procedimiento interno aplicable', but the actual procedure HR follows is not detailed and is noted as restricted/internal, leaving a key aspect missing."

**Attempt 2** — query: 'Procedimiento interno ES-007 para aprobación de solicitudes de formación que exceden el presupuesto ordinario en España: pasos de revisión de RR. HH.'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:12 | 0.4184 | 0.9991 |
| ES-004:1.0:6 | 0.4041 | 0.9947 |
| ES-001:1.0:8 | 0.4140 | 0.9924 |
| ES-001:1.0:10 | 0.4324 | 0.9912 |
| ES-002:1.0:11 | 0.3603 | 0.9762 |
| GLB-002:1.0:11 | 0.4180 | 0.9688 |
| ES-004:1.0:7 | 0.4273 | 0.8987 |
| ES-004:1.0:5 | 0.3872 | 0.7082 |
| ES-004:1.0:14 | 0.4454 | 0.7021 |
| ES-004:1.0:4 | 0.4393 | 0.2438 |

- kept: ['ES-004:1.0:12', 'ES-004:1.0:3', 'ES-004:1.0:6']
- discarded: ['ES-001:1.0:8', 'ES-001:1.0:10', 'ES-002:1.0:11', 'GLB-002:1.0:11', 'ES-004:1.0:7', 'ES-004:1.0:5', 'ES-004:1.0:14', 'ES-004:1.0:4']
- covered_aspects: ['General rule that costs exceeding the 1.200€ budget require prior exceptional approval before incurring the expense', 'Confirmation that an exception does not automatically extend to other cases or modify general limits', 'Note that certification costs over budget specifically require an exceptional evaluation request']
- missing_aspects: ['The concrete internal procedure/steps HR follows to evaluate an over-budget training request', 'Who within HR handles the review and what criteria or documentation are used (likely detailed in a restricted internal procedures document such as ES-007)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Fragments confirm that exceeding the 1.200€ training budget triggers an individual exceptional review and that approval must precede the expense, but none describe the actual internal procedure HR uses to conduct that review, leaving a key aspect missing.'

**Attempt 3** — query: 'Criterios y responsables de RR. HH. para evaluar documentación y aprobar solicitudes de formación por encima de 1.200 € anuales en España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:3 | 0.3601 | 0.9904 |
| ES-002:1.0:12 | 0.4211 | 0.8928 |
| ES-004:1.0:5 | 0.3796 | 0.8872 |
| ES-001:1.0:8 | 0.4522 | 0.8430 |
| ES-004:1.0:12 | 0.4344 | 0.5255 |
| ES-004:1.0:6 | 0.3823 | 0.4277 |
| ES-002:1.0:8 | 0.4573 | 0.2903 |
| ES-004:1.0:14 | 0.4359 | 0.2281 |
| ES-004:1.0:7 | 0.4412 | 0.0117 |
| ES-004:1.0:4 | 0.4582 | 0.0088 |

- kept: ['ES-004:1.0:12', 'ES-004:1.0:3', 'ES-004:1.0:6']
- discarded: ['ES-002:1.0:12', 'ES-004:1.0:5', 'ES-001:1.0:8', 'ES-002:1.0:8', 'ES-004:1.0:14', 'ES-004:1.0:7', 'ES-004:1.0:4']
- covered_aspects: ['Existencia de límite de 1.200€ anual', 'Necesidad de solicitar evaluación excepcional antes de comprometer el gasto si se supera el presupuesto', 'Indicación de que no hay derecho automático a financiación del exceso', 'Rol general de RRHH y áreas administrativas en validar excepciones']
- missing_aspects: ['Pasos concretos o procedimiento interno detallado que sigue RR.HH. para evaluar una solicitud excepcional', 'Criterios específicos de evaluación o plazos del proceso', 'Documento o sistema donde se detalla el procedimiento interno aplicable']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos confirman que existe un procedimiento de evaluación excepcional cuando se supera el presupuesto, pero no detallan los pasos concretos que sigue RR.HH., dejando esa aspecto sin cubrir.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### val-12 — spain-hr (expected: abstain)

**Question:** Como responsable de RR. HH. de España, ¿puede un empleado de México teletrabajar temporalmente desde otro estado de México, y qué condiciones se aplican?

**Expected answer summary:** —
**Expected aspects:** ['Existe una regla real en MX-002 §7 sobre teletrabajo desde otro estado de México, pero no es accesible para este perfil']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Como responsable de RR. HH. de España, ¿puede un empleado de México teletrabajar temporalmente desde otro estado de México, y qué condiciones se aplican?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-007:1.0:6 | 0.3366 | 0.9990 |
| ES-003:1.0:5 | 0.3443 | 0.9982 |
| ES-003:1.0:6 | 0.3895 | 0.9958 |
| GLB-002:1.0:7 | 0.3960 | 0.9949 |
| ES-004:1.0:2 | 0.4230 | 0.9927 |
| ES-005:1.0:10 | 0.4249 | 0.9907 |
| ES-003:1.0:7 | 0.4189 | 0.9881 |
| ES-003:1.0:3 | 0.4278 | 0.9780 |
| GLB-001:1.0:12 | 0.4254 | 0.9684 |
| ES-006:1.0:8 | 0.4165 | 0.1167 |

- kept: []
- discarded: ['ES-007:1.0:6', 'ES-003:1.0:5', 'ES-003:1.0:6', 'GLB-002:1.0:7', 'ES-004:1.0:2', 'ES-005:1.0:10', 'ES-003:1.0:7', 'ES-003:1.0:3', 'GLB-001:1.0:12', 'ES-006:1.0:8']
- covered_aspects: []
- missing_aspects: ['Mexico-specific telework policy conditions for working from another state within Mexico', "confirmation that Spain's ES-003 does not apply to Mexico employees"]
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: "All substantive fragments describe Spain's (ES-003/ES-007) or global (GLB-001/GLB-002) policies; ES-004 only notes that Mexico has its own distinct policy without detailing it, so no fragment actually answers the question about intra-Mexico telework conditions."

**Attempt 2** — query: 'Política de teletrabajo temporal para empleados de México dentro del país: requisitos y condiciones para trabajar desde otro estado'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-007:1.0:6 | 0.3633 | 0.9824 |
| ES-004:1.0:2 | 0.3986 | 0.9673 |
| ES-003:1.0:6 | 0.3316 | 0.9303 |
| ES-003:1.0:2 | 0.4074 | 0.9295 |
| ES-003:1.0:5 | 0.3774 | 0.8923 |
| ES-003:1.0:12 | 0.4123 | 0.8415 |
| ES-004:1.0:9 | 0.4024 | 0.5040 |
| GLB-002:1.0:7 | 0.3958 | 0.4100 |
| ES-005:1.0:10 | 0.4046 | 0.2289 |
| ES-003:1.0:1 | 0.3948 | 0.0609 |

- kept: ['ES-004:1.0:2']
- discarded: ['ES-007:1.0:6', 'ES-003:1.0:6', 'ES-003:1.0:2', 'ES-003:1.0:5', 'ES-003:1.0:12', 'ES-004:1.0:9', 'GLB-002:1.0:7', 'ES-005:1.0:10', 'ES-003:1.0:1']
- covered_aspects: ["Spain's policy explicitly states Mexico's teleworking policy may differ and is not interchangeable with Spain's rules"]
- missing_aspects: ["Actual content of Mexico's (MX) telework policy regarding domestic relocation between Mexican states", "Specific conditions, approval process, or eligibility criteria under Mexico's policy for temporary telework from another state"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Only ES-004 notes that Mexico's policy differs from Spain's and isn't interchangeable, but no fragment provides the actual Mexican policy's conditions for temporary intra-country telework, leaving the core of the question unanswered."

**Attempt 3** — query: 'Política de teletrabajo México: condiciones, proceso de aprobación y requisitos para empleados que trabajan temporalmente desde un estado distinto dentro del país'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-007:1.0:6 | 0.3294 | 0.9881 |
| ES-003:1.0:10 | 0.3566 | 0.9843 |
| ES-003:1.0:6 | 0.3036 | 0.8900 |
| ES-004:1.0:2 | 0.3622 | 0.8879 |
| ES-003:1.0:7 | 0.3464 | 0.8376 |
| ES-003:1.0:2 | 0.3689 | 0.4529 |
| ES-003:1.0:5 | 0.3590 | 0.3123 |
| GLB-002:1.0:7 | 0.3663 | 0.0721 |
| ES-005:1.0:10 | 0.3583 | 0.0127 |
| ES-003:1.0:1 | 0.3582 | 0.0126 |

- kept: []
- discarded: ['ES-004:1.0:2', 'ES-007:1.0:6', 'ES-003:1.0:10', 'ES-003:1.0:6', 'ES-003:1.0:7', 'ES-003:1.0:2', 'ES-003:1.0:5', 'GLB-002:1.0:7', 'ES-005:1.0:10', 'ES-003:1.0:1']
- covered_aspects: ['Confirma que la política española (ES-003) no aplica a empleados de México', 'Aclara que políticas de México e Inglaterra pueden tener condiciones distintas y no son intercambiables']
- missing_aspects: ['Contenido de la política de teletrabajo de México que regule el trabajo desde otro estado dentro del país', 'Condiciones específicas aplicables a empleados mexicanos para teletrabajo interno (dentro de México)']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Los fragmentos solo tratan de la política española ES-003 y confirman que no es aplicable a México, pero no contienen ninguna información sobre la política mexicana de teletrabajo ni sus condiciones para desplazamientos dentro del país.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---
