# CRAG Evaluation Report

- Generated: 2026-11-25T15:46:05.858496+00:00
- Variant: crag
- Dataset: docs\evaluation\crag-validation-questions.yaml
- top_k: 10  ·  max_retrievals: 3

These automatic metrics describe technical execution, outcome (answered vs. abstained), route distribution, retrieval counts, latency, and structural validity. They never claim an answer is factually correct or that its evidence is actually sufficient — see the manual_review fields below and in the JSON results file for that. An answer being produced (not abstained) is not the same thing as that answer being correct.

## Summary table

| ID | Category | Expected | Got | Routes | Retrievals | Latency (s) | Citations | Incidents |
|---|---|---|---|---|---|---:|---|---|
| val-01 | direct_evidence | answerable | answerable | sufficient | 1 | 19.05 | 1 | - |
| val-02 | direct_evidence | answerable | answerable | sufficient | 1 | 13.91 | 1 | - |
| val-03 | direct_evidence | answerable | answerable | sufficient | 1 | 12.40 | 2 | - |
| val-04 | multi_fragment | answerable | answerable | sufficient | 1 | 19.05 | 2 | - |
| val-05 | multi_fragment | answerable | answerable | sufficient | 1 | 16.62 | 2 | - |
| val-06 | multi_fragment | answerable | answerable | sufficient | 1 | 18.26 | 4 | - |
| val-07 | partially_answerable | abstain | answerable | ambiguous -> ambiguous -> sufficient | 3 | 49.14 | 1 | outcome mismatch |
| val-08 | partially_answerable | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 51.87 | 0 | - |
| val-09 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 44.46 | 0 | - |
| val-10 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 37.67 | 0 | - |
| val-11 | access_restricted | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 53.13 | 0 | - |
| val-12 | access_restricted | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 48.47 | 0 | - |

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
    "abstain_correct": 5,
    "abstain_correct_rate": 0.8333333333333334,
    "false_answers": 1,
    "false_answer_ids": [
      "val-07"
    ]
  },
  "routes": {
    "grader_route_counts": {
      "sufficient": 7,
      "ambiguous": 8,
      "insufficient": 9
    },
    "effective_route_counts": {
      "sufficient": 7,
      "ambiguous": 8,
      "insufficient": 9
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
    "mean": 32.00094242500685,
    "median": 28.35895264998544,
    "max": 53.126897499896586,
    "count": 12
  },
  "citations": {
    "total_citations_checked": 13,
    "citations_structurally_valid_rate": 1.0
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

**Answer:** Un empleado en España con flexibilidad horaria puede iniciar su jornada entre las 08:00 y las 10:00, siempre que sus funciones y su régimen individual lo permitan, respetando la duración de la jornada correspondiente. Además, se establece una franja común de colaboración de 10:00 a 14:00 para facilitar reuniones y coordinación entre los equipos.

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
- covered_aspects: ['rango horario permitido para iniciar jornada (08:00-10:00)', 'franja horaria común de colaboración (10:00-14:00)', 'aclaración de que la franja no sustituye otras reglas de jornada']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento 0 responde directamente y por completo ambas partes de la pregunta: el rango de entrada flexible y la franja común de colaboración.'

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

**Answer:** Northfern concede 1 día retribuido por asuntos personales por año natural a los empleados elegibles de México, independiente de las vacaciones.

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
- covered_aspects: ['Número de días retribuidos por asuntos personales (1 día) por año natural para empleados elegibles de México', 'Independencia respecto a vacaciones y permisos legales']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento 0 responde directamente y de forma completa a la pregunta, indicando 1 día retribuido por año natural, independiente de vacaciones.'

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

**Answer:** Northfern's typical annual calendar for England includes around 8 bank/public holidays, which are in addition to the 25 working days of paid annual leave and must not be deducted from that entitlement. However, the exact number and dates can vary by year, so employees should check the published company holiday calendar for the relevant year.

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
- covered_aspects: ['typical number of bank/public holidays (~8)', 'confirmation that bank holidays are separate from and additional to the 25-day annual leave entitlement']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragments 0 and 1 both state the typical calendar includes around 8 bank holidays, separate from and additional to the 25-day annual leave entitlement, fully answering the question.'

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

**Answer:** Según ES-003, el régimen ordinario de teletrabajo se ofrece a los puestos cuyas funciones pueden desarrollarse a distancia sin afectar a requisitos operativos, de atención presencial o de seguridad; la elegibilidad se determina según las funciones del puesto y las condiciones individuales aplicables, y no se presume por pertenecer a un departamento concreto. En cuanto a la ayuda de equipamiento, según ES-004, las personas cuyos puestos sean elegibles para teletrabajo pueden solicitar una ayuda de hasta 300 € por periodo de tres años para equipamiento autorizado destinado al trabajo remoto, de acuerdo con las condiciones del programa. Cabe destacar que este límite de 300 € no se renueva cada año y los importes no utilizados no se acumulan de un periodo a otro.

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
- covered_aspects: ['criterios de elegibilidad de funciones para teletrabajo ordinario', 'importe máximo de ayuda de equipamiento de teletrabajo']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [1] explica que la elegibilidad depende de que las funciones del puesto puedan realizarse a distancia sin afectar requisitos operativos, de atención presencial o de seguridad, y el fragmento [0] indica el importe máximo de 300€ por periodo de tres años para equipamiento, cubriendo ambas partes de la pregunta.'

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

**Answer:** No. Según la política, la aprobación de la inscripción a un evento no implica por sí sola la aprobación de un viaje ni la cobertura ilimitada de sus gastos. Además, los desplazamientos, alojamientos, dietas y reembolsos se rigen por la política de viajes y gastos (ES-005) y requieren las autorizaciones que esa política establece, incluyendo la aprobación previa del responsable directo para el viaje en sí, indicando motivo de negocio, destino, fechas y estimación de coste. Si se prevé superar los límites de dicha política, se necesita además una autorización excepcional previa.

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
- covered_aspects: ['aprobación de inscripción a evento no implica aprobación automática de viaje', 'viajes y gastos de desplazamiento se rigen por ES-005 y requieren sus propias autorizaciones', 'necesidad de aprobación previa del responsable directo para el viaje en sí']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [1] responde directamente que la aprobación de inscripción a un evento no implica aprobación del viaje ni de sus gastos, remitiendo a ES-005, y el fragmento [0] confirma que el viaje requiere su propia aprobación previa.'

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

**Answer:** Como manager en España, puedes consultar la información administrativa de ausencias de tus subordinados directos que sea necesaria para tu función, como las fechas de ausencias aprobadas, el tipo administrativo de ausencia y el estado de una solicitud. Este acceso solo aplica a tus colaboradores directos, no a empleados de otros equipos ni de otros países, por el simple hecho de ser manager.

Tienes explícitamente prohibido: acceder a registros de empleados de otros equipos; consultar diagnósticos médicos, documentación clínica o justificantes sensibles; pedir diagnósticos, informes clínicos o explicaciones médicas detalladas ante una ausencia imprevista o enfermedad; y compartir información personal en chats de equipo, documentos públicos u otros canales no autorizados. Además, los justificantes y documentos sensibles deben gestionarse exclusivamente mediante los canales autorizados de RR. HH., y no deben entregarse a través del chat de Policy Consultant.

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
- covered_aspects: ['qué información administrativa puede consultar un manager (fechas de ausencias aprobadas, tipo administrativo, estado de solicitud)', 'alcance limitado a subordinados directos', 'prohibición de acceder a datos médicos confidenciales, diagnósticos, justificantes sensibles', 'prohibición de acceder a otros equipos o países', 'principio de acceso mínimo necesario', 'prohibición de pedir diagnósticos o explicaciones médicas en ausencias imprevistas']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Los fragmentos ES-006 y ES-002 detallan explícitamente qué puede y no puede consultar un manager respecto a las ausencias de sus subordinados directos, cubriendo tanto lo permitido como lo prohibido.'

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

**Abstained:** False  ·  **Retrievals:** 3

**Answer:** Según la política, los empleados elegibles de México tienen derecho a 1 día retribuido por asuntos personales por año natural. No se acumula al año siguiente ni se convierte automáticamente en compensación económica, salvo que una disposición aplicable indique lo contrario. En cuanto a cuántos días te quedan disponibles este año en concreto, esa información no está en esta política: debes consultarla en el sistema de personal.

**Citations:**
- MX-001 v1.1 — 8. Día de asuntos personales (`MX-001:1.1:11`)

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
- covered_aspects: ['annual entitlement of 1 paid personal day per calendar year in Mexico']
- missing_aspects: ['individual remaining/available personal days for this specific year, which per the policy must be checked in the personnel system rather than in this document']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Fragment 0 clearly states the entitlement (1 day/year) but explicitly notes that individual availability must be checked in the HR system, which is not part of the retrieved documents.'

**Attempt 2** — query: 'Política de días de asuntos personales por año natural en Northfern México: cantidad anual según antigüedad y cómo consultar los días disponibles en el sistema de personal'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2349 | 0.9999 |
| MX-001:1.1:5 | 0.4238 | 0.9971 |
| MX-001:1.1:1 | 0.3720 | 0.9940 |
| MX-001:1.1:6 | 0.4270 | 0.9932 |
| MX-001:1.1:3 | 0.3617 | 0.9924 |
| MX-001:1.1:0 | 0.3595 | 0.9692 |
| MX-002:1.0:0 | 0.4188 | 0.9388 |
| MX-001:1.1:10 | 0.4599 | 0.6968 |
| GLB-001:1.0:5 | 0.4462 | 0.5277 |
| MX-002:1.0:1 | 0.4303 | 0.5050 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:5', 'MX-001:1.1:1', 'MX-001:1.1:6', 'MX-001:1.1:3', 'MX-001:1.1:0', 'MX-002:1.0:0', 'MX-001:1.1:10', 'GLB-001:1.0:5', 'MX-002:1.0:1']
- covered_aspects: ['Número de días de asuntos personales por año natural (1 día)', 'Que el saldo disponible se consulta en el sistema de personal, no en la política']
- missing_aspects: ['Saldo disponible específico del empleado en el año en curso (requiere consulta al sistema de personal individual)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento 0 responde claramente cuántos días corresponden por año natural, pero el saldo disponible concreto no puede determinarse desde la política y requiere datos individuales del sistema de personal.'

**Attempt 3** — query: 'Procedimiento para consultar el saldo individual de días de asuntos personales disponibles en el año en curso en el sistema de personal de Northfern México'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.2851 | 0.9992 |
| MX-001:1.1:6 | 0.3771 | 0.9967 |
| MX-001:1.1:0 | 0.4034 | 0.7454 |
| MX-001:1.1:1 | 0.3880 | 0.7233 |
| MX-002:1.0:0 | 0.4068 | 0.6826 |
| GLB-002:1.0:4 | 0.4587 | 0.4576 |
| MX-001:1.1:3 | 0.4111 | 0.4384 |
| GLB-001:1.0:0 | 0.4400 | 0.3795 |
| GLB-001:1.0:5 | 0.4502 | 0.2634 |
| MX-002:1.0:1 | 0.4305 | 0.0394 |

- kept: ['MX-001:1.1:11']
- discarded: ['MX-001:1.1:6', 'MX-001:1.1:0', 'MX-001:1.1:1', 'MX-002:1.0:0', 'GLB-002:1.0:4', 'MX-001:1.1:3', 'GLB-001:1.0:0', 'GLB-001:1.0:5', 'MX-002:1.0:1']
- covered_aspects: ['number of personal day entitlement per calendar year (1 day)', 'clarification that remaining/available days must be checked in the personnel system, not in this policy']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragment 0 directly states the entitlement (1 paid personal day per calendar year) and clarifies that individual availability is tracked in the personnel system rather than in this policy document, which fully answers both parts of the question.'

**Outcome check:** matches_expected=False
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
- covered_aspects: ['Requisitos del expediente para excepciones de vacaciones superiores a 15 días laborables consecutivos, incluyendo periodo solicitado y saldo disponible verificado en el sistema de personal', 'Proceso general de revisión excepcional por RR.HH. España']
- missing_aspects: ['Saldo de vacaciones disponible actualmente para la empleada específica Marta, que debe consultarse en el sistema de gestión de personal individual']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento [0] detalla exactamente qué debe recoger el expediente sobre periodo y saldo, pero ninguna fragmento contiene datos personales de saldo de Marta, ya que las políticas indican explícitamente que no contienen saldos individuales.'

**Attempt 2** — query: 'requisitos del expediente para excepción de vacaciones de más de 15 días laborables consecutivos en España: periodo solicitado y documentación del saldo de vacaciones disponible'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-007:1.0:4 | 0.3498 | 0.9995 |
| ES-001:1.0:8 | 0.3192 | 0.9994 |
| ES-001:1.0:4 | 0.3194 | 0.9985 |
| ES-006:1.0:4 | 0.3226 | 0.9980 |
| ES-001:1.0:6 | 0.2863 | 0.9950 |
| ES-002:1.0:11 | 0.3931 | 0.9897 |
| ES-001:1.0:7 | 0.3959 | 0.9749 |
| ES-006:1.0:8 | 0.3799 | 0.9739 |
| ES-002:1.0:4 | 0.4047 | 0.9727 |
| ES-005:1.0:8 | 0.4018 | 0.1348 |

- kept: ['ES-007:1.0:4']
- discarded: ['ES-001:1.0:8', 'ES-001:1.0:4', 'ES-006:1.0:4', 'ES-001:1.0:6', 'ES-002:1.0:11', 'ES-001:1.0:7', 'ES-006:1.0:8', 'ES-002:1.0:4', 'ES-005:1.0:8']
- covered_aspects: ['Qué información debe recoger el expediente sobre el periodo solicitado y saldo disponible (ES-007)', 'Procedimiento de excepción y verificación en el sistema de personal']
- missing_aspects: ['Saldo de vacaciones actual disponible para Marta (dato individual, debe consultarse en los registros corporativos/sistema de personal, no está en esta documentación)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'El fragmento ES-007 explica claramente qué debe recoger el expediente, pero ninguno de los fragmentos contiene el saldo individual de vacaciones de Marta, que según varios documentos se verifica en los registros corporativos, no en esta política.'

**Attempt 3** — query: 'consulta de saldo de vacaciones disponible de un empleado en el sistema de personal o registros corporativos de España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:3 | 0.3430 | 0.9990 |
| ES-001:1.0:9 | 0.2983 | 0.9987 |
| ES-006:1.0:4 | 0.3929 | 0.9924 |
| ES-004:1.0:4 | 0.3921 | 0.9902 |
| ES-002:1.0:11 | 0.3933 | 0.9807 |
| ES-001:1.0:7 | 0.4236 | 0.9685 |
| ES-003:1.0:12 | 0.4076 | 0.9665 |
| ES-001:1.0:5 | 0.4240 | 0.9650 |
| ES-001:1.0:8 | 0.4103 | 0.7878 |
| ES-006:1.0:3 | 0.4160 | 0.4521 |

- kept: ['ES-007:1.0:4']
- discarded: ['ES-001:1.0:3', 'ES-001:1.0:9', 'ES-006:1.0:4', 'ES-004:1.0:4', 'ES-002:1.0:11', 'ES-001:1.0:7', 'ES-003:1.0:12', 'ES-001:1.0:5', 'ES-001:1.0:8', 'ES-006:1.0:3']
- covered_aspects: ["requirements for the exception file regarding requested period and available balance (must record period requested and balance verified in the personnel system, reason for exception, manager's assessment of coverage, proposed resolution)"]
- missing_aspects: ["Marta's actual current vacation balance, which must be looked up in the personnel/corporate system and is not contained in any policy document"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment [0] fully answers what the file must record about period and balance, but no fragment contains Marta's actual personal balance since policies explicitly state individual balances are not in these documents but in the personnel system."

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
- missing_aspects: ['existencia de programa de coche de empresa o leasing de vehículo', 'condiciones de elegibilidad y requisitos para dicho beneficio', 'importes o límites asociados a ese beneficio si existe']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona coches de empresa, leasing de vehículos ni beneficios relacionados con transporte; solo cubren vacaciones, permisos, formación y viajes de negocio, sin referencia específica a este tema.'

**Attempt 2** — query: 'Política de beneficios para empleados en España: coche de empresa, leasing de vehículo, requisitos de elegibilidad y límites de importe'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:1 | 0.4012 | 0.9990 |
| ES-004:1.0:2 | 0.3915 | 0.9972 |
| ES-004:1.0:11 | 0.4243 | 0.9937 |
| ES-004:1.0:14 | 0.3810 | 0.9813 |
| GLB-002:1.0:11 | 0.4241 | 0.9474 |
| ES-002:1.0:4 | 0.4287 | 0.9375 |
| ES-004:1.0:4 | 0.4090 | 0.3772 |
| ES-002:1.0:8 | 0.4022 | 0.3397 |
| ES-005:1.0:1 | 0.3951 | 0.3052 |
| ES-004:1.0:7 | 0.4377 | 0.0009 |

- kept: []
- discarded: ['ES-004:1.0:1', 'ES-004:1.0:2', 'ES-004:1.0:11', 'ES-004:1.0:14', 'GLB-002:1.0:11', 'ES-002:1.0:4', 'ES-004:1.0:4', 'ES-002:1.0:8', 'ES-005:1.0:1', 'ES-004:1.0:7']
- covered_aspects: []
- missing_aspects: ['Existencia de programa de coche de empresa o leasing de vehículo en España', 'Condiciones de elegibilidad y requisitos para dicho beneficio, si existe']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona coches de empresa, leasing de vehículos o beneficios similares; tratan de formación, bienestar, permisos personales, viajes/gastos y seguridad de la información, sin relación directa con la pregunta.'

**Attempt 3** — query: 'Beneficios de movilidad y transporte para empleados en España: coche de empresa, leasing de vehículo, requisitos de elegibilidad'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:14 | 0.4188 | 0.9970 |
| ES-005:1.0:1 | 0.4153 | 0.9912 |
| ES-004:1.0:2 | 0.4423 | 0.9859 |
| ES-004:1.0:11 | 0.4506 | 0.9739 |
| GLB-002:1.0:11 | 0.4516 | 0.9705 |
| ES-005:1.0:12 | 0.4436 | 0.7909 |
| ES-002:1.0:4 | 0.4451 | 0.6094 |
| GLB-002:1.0:7 | 0.4255 | 0.4222 |
| ES-002:1.0:8 | 0.4301 | 0.0371 |
| ES-004:1.0:7 | 0.4424 | 0.0020 |

- kept: []
- discarded: ['ES-004:1.0:14', 'ES-005:1.0:1', 'ES-004:1.0:2', 'ES-004:1.0:11', 'GLB-002:1.0:11', 'ES-005:1.0:12', 'ES-002:1.0:4', 'GLB-002:1.0:7', 'ES-002:1.0:8', 'ES-004:1.0:7']
- covered_aspects: []
- missing_aspects: ['existencia de programa de coche de empresa o leasing de vehículo', 'condiciones de elegibilidad para beneficio de vehículo']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona coches de empresa, leasing de vehículos ni beneficios relacionados con transporte; tratan de formación, viajes/gastos, seguridad de la información y permisos, por lo que no aportan evidencia sobre la pregunta.'

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
- missing_aspects: ['relocation assistance policy or benefits', 'international transfer procedures between England, Spain, and Mexico offices']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance, international transfers, or related benefits; they cover Code of Conduct, information security, and leave policies instead.'

**Attempt 2** — query: 'international employee transfer relocation benefits policy England Spain Mexico offices'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:12 | 0.3745 | 0.8796 |
| GLB-002:1.0:11 | 0.4445 | 0.8263 |
| GLB-001:1.0:1 | 0.4704 | 0.7502 |
| GLB-001:1.0:12 | 0.3953 | 0.5189 |
| EN-001:1.0:1 | 0.3861 | 0.2705 |
| EN-001:1.0:0 | 0.4653 | 0.1388 |
| GLB-002:1.0:0 | 0.4802 | 0.0981 |
| GLB-002:1.0:7 | 0.4072 | 0.0670 |
| EN-001:1.0:9 | 0.4831 | 0.0155 |
| EN-001:1.0:7 | 0.4971 | 0.0023 |

- kept: []
- discarded: ['EN-001:1.0:12', 'GLB-002:1.0:11', 'GLB-001:1.0:1', 'GLB-001:1.0:12', 'EN-001:1.0:1', 'EN-001:1.0:0', 'GLB-002:1.0:0', 'GLB-002:1.0:7', 'EN-001:1.0:9', 'EN-001:1.0:7']
- covered_aspects: []
- missing_aspects: ['existence of a relocation assistance policy or benefit', 'terms of international relocation support for England, Spain, or Mexico employees']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance or international transfer benefits; they cover leave, code of conduct, and information security policies instead.'

**Attempt 3** — query: 'relocation assistance benefit policy for employees transferring between England, Spain, and Mexico offices'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:12 | 0.4110 | 0.9351 |
| GLB-001:1.0:1 | 0.4668 | 0.6629 |
| GLB-001:1.0:12 | 0.4111 | 0.2366 |
| GLB-002:1.0:11 | 0.4392 | 0.1237 |
| EN-001:1.0:0 | 0.5048 | 0.0910 |
| EN-001:1.0:1 | 0.4406 | 0.0412 |
| GLB-002:1.0:0 | 0.5181 | 0.0214 |
| EN-001:1.0:9 | 0.5237 | 0.0078 |
| EN-001:1.0:5 | 0.5346 | 0.0063 |
| GLB-002:1.0:7 | 0.4420 | 0.0041 |

- kept: []
- discarded: ['EN-001:1.0:12', 'GLB-001:1.0:1', 'GLB-001:1.0:12', 'GLB-002:1.0:11', 'EN-001:1.0:0', 'EN-001:1.0:1', 'GLB-002:1.0:0', 'EN-001:1.0:9', 'EN-001:1.0:5', 'GLB-002:1.0:7']
- covered_aspects: []
- missing_aspects: ['existence of a relocation assistance policy or package', 'eligibility criteria for international relocation support', 'financial or logistical benefits provided for relocating between countries']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments discuss relocation assistance or international transfer benefits; they cover leave, code of conduct, and information security policies instead.'

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
- covered_aspects: ['Confirma que gastos de formación por encima del presupuesto de 1.200€ requieren evaluación excepcional previa', 'Indica que la solicitud debe plantearse antes de inscribirse o gastar', 'Aclara que una excepción concedida no modifica los límites generales ni crea derecho para otros']
- missing_aspects: ['Detalle concreto del procedimiento interno de evaluación de excepciones (pasos, plazos, responsables específicos)', 'Quién dentro de RR.HH. o qué área administrativa interviene exactamente en la revisión', 'Criterios usados para decidir si se aprueba el exceso de presupuesto']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Los fragmentos confirman que existe un proceso de evaluación excepcional para gastos de formación que superan el presupuesto, pero remiten a un 'procedimiento interno aplicable' sin detallar los pasos concretos que sigue RR.HH."

**Attempt 2** — query: 'Procedimiento interno de excepción presupuestaria en formación: pasos, plazos, responsables de RR. HH. y criterios de aprobación para solicitudes que superen 1.200 € anuales en España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:12 | 0.3786 | 0.9987 |
| ES-001:1.0:8 | 0.3687 | 0.9986 |
| ES-004:1.0:6 | 0.4017 | 0.9965 |
| ES-004:1.0:5 | 0.3514 | 0.9919 |
| ES-005:1.0:8 | 0.4269 | 0.9895 |
| ES-002:1.0:11 | 0.4149 | 0.9885 |
| ES-004:1.0:3 | 0.3803 | 0.9826 |
| ES-002:1.0:4 | 0.4256 | 0.7127 |
| ES-005:1.0:9 | 0.4246 | 0.5511 |
| ES-004:1.0:4 | 0.4263 | 0.0639 |

- kept: ['ES-004:1.0:12', 'ES-004:1.0:3', 'ES-004:1.0:6']
- discarded: ['ES-001:1.0:8', 'ES-004:1.0:5', 'ES-005:1.0:8', 'ES-002:1.0:11', 'ES-002:1.0:4', 'ES-005:1.0:9', 'ES-004:1.0:4']
- covered_aspects: ['Budget limit of 1,200€ annually for training', 'Requirement to request exceptional evaluation before incurring expense exceeding budget', 'No automatic right to excess financing', "General principle that exceptions don't modify general limits"]
- missing_aspects: ['Specific internal procedure/steps HR follows to review an exceptional training budget request', 'Who specifically evaluates and approves the exception (roles, timeline, documentation required)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragments confirm that exceeding the 1,200€ training budget requires a prior exceptional request/evaluation, but none detail the actual internal procedure HR follows to review such requests, only referencing it as 'procedimiento interno aplicable' without specifics."

**Attempt 3** — query: 'Revisión de solicitudes de formación que exceden el presupuesto anual: roles responsables, documentación requerida y plazos de aprobación en RR. HH. España'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-004:1.0:6 | 0.3509 | 0.9990 |
| ES-004:1.0:12 | 0.3685 | 0.9989 |
| ES-002:1.0:12 | 0.4011 | 0.9399 |
| ES-004:1.0:13 | 0.4083 | 0.9181 |
| ES-004:1.0:5 | 0.3654 | 0.7921 |
| ES-001:1.0:5 | 0.4092 | 0.7867 |
| ES-001:1.0:8 | 0.4124 | 0.7481 |
| ES-004:1.0:7 | 0.4161 | 0.5054 |
| ES-002:1.0:11 | 0.3844 | 0.4125 |
| ES-002:1.0:8 | 0.3866 | 0.0623 |

- kept: ['ES-004:1.0:12', 'ES-004:1.0:3', 'ES-004:1.0:6']
- discarded: ['ES-002:1.0:12', 'ES-004:1.0:13', 'ES-004:1.0:5', 'ES-001:1.0:5', 'ES-001:1.0:8', 'ES-004:1.0:7', 'ES-002:1.0:11', 'ES-002:1.0:8']
- covered_aspects: ['Presupuesto anual de 1.200€ y su carácter no acumulable', 'Requisito de aprobación previa para gastos que excedan el presupuesto', 'Necesidad de solicitar evaluación excepcional antes de comprometer el gasto', 'Principio general de que las excepciones se valoran individualmente y no generan derechos automáticos']
- missing_aspects: ['Procedimiento interno detallado que sigue RR. HH. para evaluar estas solicitudes excepcionales (pasos, criterios, plazos)', 'Documento o referencia específica que describa el proceso interno de excepciones (p.ej. ES-007 de procedimientos internos de RR. HH.)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos confirman que existe un proceso de evaluación excepcional para gastos de formación que superan el presupuesto, pero no detallan el procedimiento interno específico que sigue RR. HH., que parece estar en un documento de acceso restringido no incluido.'

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
- missing_aspects: ['Mexico-specific telework policy document', 'conditions for domestic relocation within Mexico for telework', 'applicable authorization or notification requirements under Mexico HR policy']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: "All retrieved fragments concern Spain (ES-003, ES-004, ES-005, ES-006, ES-007) or global policies (GLB-001, GLB-002), with no document addressing Mexico's domestic telework rules, so none can answer this Mexico-specific question."

**Attempt 2** — query: 'Política de teletrabajo México: requisitos y autorización para reubicación temporal dentro del país'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-003:1.0:7 | 0.3948 | 0.9841 |
| ES-003:1.0:10 | 0.3891 | 0.9806 |
| ES-007:1.0:6 | 0.3770 | 0.9272 |
| ES-003:1.0:6 | 0.3904 | 0.8889 |
| ES-003:1.0:12 | 0.3993 | 0.6190 |
| ES-005:1.0:10 | 0.3925 | 0.5670 |
| ES-004:1.0:2 | 0.4096 | 0.5476 |
| GLB-002:1.0:7 | 0.4121 | 0.5395 |
| ES-004:1.0:9 | 0.3951 | 0.4920 |
| ES-003:1.0:1 | 0.4055 | 0.0606 |

- kept: []
- discarded: ['ES-003:1.0:7', 'ES-003:1.0:10', 'ES-007:1.0:6', 'ES-003:1.0:6', 'ES-003:1.0:12', 'ES-005:1.0:10', 'ES-004:1.0:2', 'GLB-002:1.0:7', 'ES-004:1.0:9', 'ES-003:1.0:1']
- covered_aspects: []
- missing_aspects: ['México-specific telework policy (not ES-003, which only applies to Spain)', 'conditions for teleworking from a different state within Mexico', 'whether moving within the same country requires authorization']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: "All retrieved fragments concern Spain's ES-003 policy and cross-border telework from Spain; one fragment explicitly notes Mexico's policy is distinct and not interchangeable, but no fragment actually provides Mexico's own rules for intra-country relocation, so nothing here answers the question."

**Attempt 3** — query: 'Normativa de teletrabajo para empleados de México: condiciones y autorización para trabajar desde un estado distinto dentro del mismo país'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-003:1.0:10 | 0.4153 | 0.9906 |
| ES-007:1.0:6 | 0.3422 | 0.9571 |
| ES-003:1.0:6 | 0.3450 | 0.8626 |
| ES-003:1.0:7 | 0.3821 | 0.8579 |
| ES-004:1.0:9 | 0.4021 | 0.7299 |
| ES-003:1.0:2 | 0.3890 | 0.6446 |
| GLB-002:1.0:7 | 0.3509 | 0.6061 |
| ES-003:1.0:5 | 0.3332 | 0.5382 |
| ES-005:1.0:10 | 0.3728 | 0.4194 |
| ES-003:1.0:1 | 0.4278 | 0.2649 |

- kept: []
- discarded: ['ES-003:1.0:10', 'ES-007:1.0:6', 'ES-003:1.0:6', 'ES-003:1.0:7', 'ES-004:1.0:9', 'ES-003:1.0:2', 'GLB-002:1.0:7', 'ES-003:1.0:5', 'ES-005:1.0:10', 'ES-003:1.0:1']
- covered_aspects: []
- missing_aspects: ['whether ES-003 applies to employees based in Mexico', 'local Mexico telework/flexibility policy for domestic interstate relocation', 'conditions for teleworking within Mexico (not from Mexico to another country)']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: "All fragments pertain specifically to ES-003, which explicitly governs employees based in Spain, and to international (cross-country) telework scenarios; none address a Mexico-based employee's domestic interstate telework, so they don't help answer this question."

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---
