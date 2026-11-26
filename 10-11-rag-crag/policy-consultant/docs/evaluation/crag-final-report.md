# CRAG Evaluation Report

- Generated: 2026-11-26T16:01:29.996486+00:00
- Variant: crag
- Dataset: docs\evaluation\crag-evaluation-questions.yaml
- top_k: 10  ·  max_retrievals: 3

These automatic metrics describe technical execution, outcome (answered vs. abstained), route distribution, retrieval counts, latency, and structural validity. They never claim an answer is factually correct or that its evidence is actually sufficient — see the manual_review fields below and in the JSON results file for that. An answer being produced (not abstained) is not the same thing as that answer being correct.

## Summary table

| ID | Category | Expected | Got | Routes | Retrievals | Latency (s) | Citations | Incidents |
|---|---|---|---|---|---|---:|---|---|
| eval-crag-01 | direct_evidence | answerable | answerable | sufficient | 1 | 17.46 | 2 | - |
| eval-crag-02 | direct_evidence | answerable | answerable | sufficient | 1 | 17.43 | 2 | - |
| eval-crag-03 | direct_evidence | answerable | answerable | sufficient | 1 | 14.17 | 1 | - |
| eval-crag-04 | direct_evidence | answerable | answerable | sufficient | 1 | 15.56 | 1 | - |
| eval-crag-05 | direct_evidence | answerable | answerable | sufficient | 1 | 14.36 | 1 | - |
| eval-crag-06 | direct_evidence | answerable | answerable | sufficient | 1 | 11.23 | 1 | - |
| eval-crag-07 | direct_evidence | answerable | answerable | sufficient | 1 | 18.55 | 1 | - |
| eval-crag-08 | multi_fragment | answerable | answerable | sufficient | 1 | 20.10 | 5 | - |
| eval-crag-09 | multi_fragment | answerable | answerable | sufficient | 1 | 23.39 | 4 | - |
| eval-crag-10 | multi_fragment | answerable | answerable | sufficient | 1 | 23.15 | 3 | - |
| eval-crag-11 | multi_fragment | answerable | answerable | sufficient | 1 | 21.25 | 2 | expected evidence missing from final context |
| eval-crag-12 | multi_fragment | answerable | answerable | sufficient | 1 | 24.06 | 3 | - |
| eval-crag-13 | multi_fragment | answerable | answerable | ambiguous -> ambiguous -> sufficient | 3 | 42.92 | 2 | - |
| eval-crag-14 | multi_fragment | answerable | answerable | sufficient | 1 | 20.30 | 2 | - |
| eval-crag-15 | partially_answerable | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 46.25 | 0 | - |
| eval-crag-16 | partially_answerable | abstain | abstain | ambiguous -> ambiguous -> ambiguous | 3 | 42.53 | 0 | - |
| eval-crag-17 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 33.51 | 0 | - |
| eval-crag-18 | no_information | abstain | abstain | insufficient -> insufficient -> insufficient | 3 | 37.59 | 0 | - |
| eval-crag-19 | access_restricted | abstain | abstain | insufficient -> ambiguous -> ambiguous | 3 | 43.11 | 0 | - |
| eval-crag-20 | access_restricted | abstain | abstain | ambiguous -> ambiguous -> insufficient | 3 | 43.94 | 0 | - |

## Automatic metrics

```json
{
  "total_questions": 20,
  "technical_errors": {
    "count": 0,
    "ids": []
  },
  "executed_successfully": {
    "count": 20,
    "ids": [
      "eval-crag-01",
      "eval-crag-02",
      "eval-crag-03",
      "eval-crag-04",
      "eval-crag-05",
      "eval-crag-06",
      "eval-crag-07",
      "eval-crag-08",
      "eval-crag-09",
      "eval-crag-10",
      "eval-crag-11",
      "eval-crag-12",
      "eval-crag-13",
      "eval-crag-14",
      "eval-crag-15",
      "eval-crag-16",
      "eval-crag-17",
      "eval-crag-18",
      "eval-crag-19",
      "eval-crag-20"
    ]
  },
  "outcome": {
    "answerable_total": 14,
    "answerable_executed": 14,
    "answerable_technical_errors": 0,
    "answerable_answered": 14,
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
      "sufficient": 14,
      "ambiguous": 12,
      "insufficient": 8
    },
    "effective_route_counts": {
      "sufficient": 14,
      "ambiguous": 12,
      "insufficient": 8
    },
    "route_divergences": []
  },
  "retrievals": {
    "distribution": {
      "1": 13,
      "3": 7
    },
    "mean": 1.7,
    "questions_needing_reformulation": 7
  },
  "latency_seconds": {
    "mean": 26.542880330001935,
    "median": 22.201107449945994,
    "max": 46.25090440013446,
    "count": 20
  },
  "citations": {
    "total_citations_checked": 30,
    "citations_structurally_valid_rate": 1.0,
    "citations_from_final_context_rate": 1.0
  },
  "evidence_coverage": {
    "answerable_with_evidence": 14,
    "coverage_in_final_context_at_k": 0.9523809523809523,
    "coverage_ever_retrieved_at_k": 0.9523809523809523,
    "pct_all_found_in_final_context": 0.9285714285714286
  }
}
```

## Per-question detail

### eval-crag-01 — spain-employee (expected: answerable)

**Question:** ¿Con cuánta antelación debo solicitar mis vacaciones en España antes del primer día que quiero disfrutar?

**Expected answer summary:** Con al menos 15 días naturales de antelación respecto al primer día previsto de disfrute, salvo que se aplique una excepción justificada.
**Expected aspects:** ['Plazo ordinario de antelación: 15 días naturales']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** En España, las vacaciones deben solicitarse con al menos 15 días naturales de antelación respecto al primer día previsto de disfrute, indicando las fechas de inicio y fin, y comprobando previamente que se dispone de saldo suficiente. Este plazo ordinario puede exceptuarse ante circunstancias justificadas (por ejemplo, solicitudes con menos de 15 días de antelación), siguiendo el procedimiento de excepciones: comunicarlo al responsable directo, quien evaluará el impacto y, si corresponde, trasladará el caso a Recursos Humanos de España. Ninguna excepción se considera aprobada automáticamente por el mero hecho de solicitarla; debe confirmarse por los canales internos establecidos.

**Citations:**
- ES-001 v1.0 — 4. Solicitud de vacaciones (`ES-001:1.0:4`)
- ES-001 v1.0 — 8. Excepciones (`ES-001:1.0:8`)

**Attempt 1** — query: '¿Con cuánta antelación debo solicitar mis vacaciones en España antes del primer día que quiero disfrutar?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:4 | 0.2453 | 0.9992 |
| ES-001:1.0:8 | 0.3481 | 0.9990 |
| ES-002:1.0:4 | 0.4093 | 0.9966 |
| ES-002:1.0:7 | 0.3920 | 0.9963 |
| ES-002:1.0:11 | 0.4365 | 0.9882 |
| ES-001:1.0:7 | 0.3789 | 0.9783 |
| ES-001:1.0:0 | 0.4367 | 0.8850 |
| ES-001:1.0:9 | 0.4089 | 0.8772 |
| ES-001:1.0:6 | 0.3780 | 0.7807 |
| ES-005:1.0:3 | 0.4175 | 0.0259 |

- kept: ['ES-001:1.0:4', 'ES-001:1.0:8']
- discarded: ['ES-002:1.0:4', 'ES-002:1.0:7', 'ES-002:1.0:11', 'ES-001:1.0:7', 'ES-001:1.0:0', 'ES-001:1.0:9', 'ES-001:1.0:6', 'ES-005:1.0:3']
- covered_aspects: ['Plazo ordinario de antelación para solicitar vacaciones (15 días naturales)', 'Excepciones al plazo ordinario y procedimiento aplicable']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento 0 responde directamente a la pregunta indicando el plazo de 15 días naturales, y el fragmento 1 complementa explicando el procedimiento de excepción cuando no se cumple ese plazo.'

**Expected evidence:**
- ES-001:1.0:4: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-02 — spain-manager (expected: answerable)

**Question:** Como manager en España, si uno de mis colaboradores disfruta sus dos días anuales retribuidos por asuntos personales, ¿puedo descontarlos de su saldo de vacaciones?

**Expected answer summary:** No. Debo distinguir los dos días anuales retribuidos por asuntos personales de ES-002 de las vacaciones de ES-001, y no debo descontar automáticamente ese tipo de ausencia del saldo de vacaciones.
**Expected aspects:** ['Los días de asuntos personales son distintos de las vacaciones', 'No deben descontarse automáticamente del saldo de vacaciones']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** No. Los dos días anuales retribuidos por asuntos personales (regulados en ES-002) son un beneficio adicional distinto de las vacaciones reguladas en ES-001, y no se descuentan del saldo de vacaciones. Además, como manager, no debe descontar automáticamente una ausencia del saldo de vacaciones; la clasificación y el registro deben corresponder al tipo de ausencia reconocido por la política y, cuando proceda, ser validados por Recursos Humanos.

**Citations:**
- ES-002 v1.0 — 4. Permiso interno por asuntos personales (`ES-002:1.0:4`)
- ES-006 v1.0 — 5. Ausencias planificadas (`ES-006:1.0:5`)

**Attempt 1** — query: 'Como manager en España, si uno de mis colaboradores disfruta sus dos días anuales retribuidos por asuntos personales, ¿puedo descontarlos de su saldo de vacaciones?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-002:1.0:4 | 0.3210 | 0.9997 |
| ES-006:1.0:5 | 0.3411 | 0.9991 |
| ES-001:1.0:9 | 0.3282 | 0.9988 |
| ES-001:1.0:3 | 0.3550 | 0.9972 |
| ES-001:1.0:8 | 0.3675 | 0.9949 |
| ES-006:1.0:4 | 0.3373 | 0.9896 |
| ES-006:1.0:8 | 0.3527 | 0.9849 |
| ES-006:1.0:2 | 0.4026 | 0.6951 |
| ES-006:1.0:3 | 0.4005 | 0.5087 |
| ES-005:1.0:6 | 0.4068 | 0.0005 |

- kept: ['ES-002:1.0:4', 'ES-006:1.0:5']
- discarded: ['ES-001:1.0:9', 'ES-001:1.0:3', 'ES-001:1.0:8', 'ES-006:1.0:4', 'ES-006:1.0:8', 'ES-006:1.0:2', 'ES-006:1.0:3', 'ES-005:1.0:6']
- covered_aspects: ['definición y naturaleza de los dos días retribuidos por asuntos personales (ES-002)', 'regla explícita de que no se descuentan del saldo de vacaciones (ES-001)', 'instrucción directa al manager de no descontar automáticamente esta ausencia del saldo de vacaciones (ES-006)']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Los fragmentos 0 y 1 responden directamente la pregunta: los días de asuntos personales no se descuentan del saldo de vacaciones y el manager no debe hacerlo, cubriendo completamente la consulta.'

**Expected evidence:**
- ES-006:1.0:5: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-03 — spain-employee (expected: answerable)

**Question:** Si necesito ausentarme de mi puesto en España por una cita médica, ¿durante cuánto tiempo puedo comunicar la ausencia y debo avisar con antelación?

**Expected answer summary:** Puede comunicarse una ausencia por el tiempo indispensable que requiera la cita; siempre que sea posible, debe avisarse con antelación al responsable directo para coordinar el trabajo pendiente.
**Expected aspects:** ['Duración: el tiempo indispensable para la cita', 'Aviso previo al responsable directo cuando sea posible']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Puede comunicar la ausencia por el tiempo indispensable para la cita médica. Además, siempre que sea posible, debe avisar con antelación a su responsable para coordinar el trabajo pendiente.

**Citations:**
- ES-002 v1.0 — 5. Citas médicas (`ES-002:1.0:5`)

**Attempt 1** — query: 'Si necesito ausentarme de mi puesto en España por una cita médica, ¿durante cuánto tiempo puedo comunicar la ausencia y debo avisar con antelación?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-002:1.0:5 | 0.2801 | 0.9996 |
| ES-001:1.0:8 | 0.3878 | 0.9993 |
| ES-002:1.0:7 | 0.3981 | 0.9990 |
| ES-002:1.0:11 | 0.3933 | 0.9963 |
| ES-002:1.0:3 | 0.3478 | 0.9952 |
| ES-002:1.0:6 | 0.3681 | 0.9900 |
| ES-001:1.0:2 | 0.4184 | 0.9787 |
| ES-002:1.0:9 | 0.4274 | 0.8947 |
| ES-001:1.0:4 | 0.4031 | 0.4225 |
| ES-005:1.0:8 | 0.4266 | 0.0025 |

- kept: ['ES-002:1.0:5']
- discarded: ['ES-001:1.0:8', 'ES-002:1.0:7', 'ES-002:1.0:11', 'ES-002:1.0:3', 'ES-002:1.0:6', 'ES-001:1.0:2', 'ES-002:1.0:9', 'ES-001:1.0:4', 'ES-005:1.0:8']
- covered_aspects: ['duración de la ausencia por cita médica (tiempo indispensable)', 'obligación de avisar con antelación al responsable cuando sea posible']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento 0 responde directamente ambas partes de la pregunta: la ausencia se comunica por el tiempo indispensable y se debe avisar con antelación al responsable cuando sea posible.'

**Expected evidence:**
- ES-002:1.0:5: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-04 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, ¿en qué plazo debe presentar un empleado los gastos de un viaje de trabajo después de finalizarlo?

**Expected answer summary:** Dentro de los 15 días naturales posteriores a la finalización del viaje, a través del canal corporativo autorizado, y con un justificante válido para cada gasto.
**Expected aspects:** ['Plazo de presentación: 15 días naturales tras finalizar el viaje']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Los gastos deben presentarse a través del canal corporativo autorizado dentro de los 15 días naturales posteriores a la finalización del viaje.

**Citations:**
- ES-005 v1.0 — 8. Justificantes y presentación de gastos (`ES-005:1.0:8`)

**Attempt 1** — query: 'Como responsable de RR. HH. en España, ¿en qué plazo debe presentar un empleado los gastos de un viaje de trabajo después de finalizarlo?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:8 | 0.3339 | 0.9995 |
| ES-005:1.0:6 | 0.3875 | 0.9888 |
| ES-007:1.0:4 | 0.3433 | 0.9438 |
| ES-001:1.0:8 | 0.3753 | 0.7455 |
| ES-002:1.0:12 | 0.3995 | 0.7334 |
| ES-006:1.0:12 | 0.3817 | 0.7259 |
| ES-002:1.0:11 | 0.3923 | 0.6573 |
| ES-002:1.0:7 | 0.4098 | 0.0848 |
| ES-006:1.0:8 | 0.3639 | 0.0775 |
| ES-006:1.0:4 | 0.3679 | 0.0669 |

- kept: ['ES-005:1.0:8']
- discarded: ['ES-005:1.0:6', 'ES-007:1.0:4', 'ES-001:1.0:8', 'ES-002:1.0:12', 'ES-006:1.0:12', 'ES-002:1.0:11', 'ES-002:1.0:7', 'ES-006:1.0:8', 'ES-006:1.0:4']
- covered_aspects: ['Plazo de presentación de gastos de viaje tras finalización']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragment [0] directly states the 15-calendar-day deadline for submitting travel expenses after trip completion, fully answering the question.'

**Expected evidence:**
- ES-005:1.0:8: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-05 — mexico-employee (expected: answerable)

**Question:** ¿Con cuántos días naturales de antelación debo presentar, como regla interna, una solicitud ordinaria de vacaciones en México?

**Expected answer summary:** Con al menos 10 días naturales de antelación, como regla de planificación interna, siempre que sea compatible con los derechos y plazos legales aplicables.
**Expected aspects:** ['Plazo de antelación recomendado: 10 días naturales']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Como regla de planificación interna, en México las solicitudes ordinarias de vacaciones deben presentarse con al menos 10 días naturales de antelación, siempre que ello sea compatible con los derechos y plazos legales aplicables. Esta recomendación de antelación no elimina los derechos de disfrute del empleado ni habilita denegaciones contrarias a la legislación aplicable.

**Citations:**
- MX-001 v1.1 — 5. Solicitud ordinaria de vacaciones (`MX-001:1.1:8`)

**Attempt 1** — query: '¿Con cuántos días naturales de antelación debo presentar, como regla interna, una solicitud ordinaria de vacaciones en México?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:8 | 0.3327 | 0.9998 |
| MX-001:1.1:10 | 0.3423 | 0.9965 |
| MX-001:1.1:1 | 0.4066 | 0.9952 |
| MX-001:1.1:11 | 0.4123 | 0.9794 |
| MX-001:1.1:9 | 0.4189 | 0.9755 |
| MX-001:1.1:0 | 0.4298 | 0.9443 |
| MX-001:1.1:12 | 0.4350 | 0.6029 |
| MX-001:1.1:5 | 0.4586 | 0.3811 |
| MX-002:1.0:6 | 0.4548 | 0.3046 |
| MX-002:1.0:8 | 0.4403 | 0.0069 |

- kept: ['MX-001:1.1:8']
- discarded: ['MX-001:1.1:10', 'MX-001:1.1:1', 'MX-001:1.1:11', 'MX-001:1.1:9', 'MX-001:1.1:0', 'MX-001:1.1:12', 'MX-001:1.1:5', 'MX-002:1.0:6', 'MX-002:1.0:8']
- covered_aspects: ['Plazo de antelación interno para solicitudes ordinarias de vacaciones en México (10 días naturales)']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'El fragmento [0] responde directamente a la pregunta indicando la regla interna de 10 días naturales de antelación para solicitudes ordinarias de vacaciones en México.'

**Expected evidence:**
- MX-001:1.1:8: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-06 — england-employee (expected: answerable)

**Question:** In England, what is the maximum number of consecutive working days of annual leave I can ordinarily request without needing special approval?

**Expected answer summary:** Up to 10 consecutive working days ordinarily; longer periods require advance discussion and special approval from the line manager in coordination with England HR.
**Expected aspects:** ['Ordinary maximum: up to 10 consecutive working days', 'Longer periods require advance discussion and special approval']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** In England, employees may ordinarily request up to 10 consecutive working days of annual leave without needing special approval. Longer periods require advance discussion and special approval from the line manager in coordination with England HR.

**Citations:**
- EN-001 v1.0 — 5. Consecutive leave and team coverage (`EN-001:1.0:5`)

**Attempt 1** — query: 'In England, what is the maximum number of consecutive working days of annual leave I can ordinarily request without needing special approval?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:5 | 0.2509 | 0.9999 |
| EN-001:1.0:6 | 0.4102 | 0.9954 |
| EN-001:1.0:2 | 0.3612 | 0.9873 |
| EN-001:1.0:1 | 0.4081 | 0.9361 |
| EN-001:1.0:7 | 0.3691 | 0.8619 |
| EN-001:1.0:4 | 0.4498 | 0.7113 |
| EN-001:1.0:0 | 0.4855 | 0.6858 |
| EN-001:1.0:3 | 0.4616 | 0.2271 |
| EN-001:1.0:10 | 0.4030 | 0.1165 |
| EN-001:1.0:9 | 0.4263 | 0.0437 |

- kept: ['EN-001:1.0:5']
- discarded: ['EN-001:1.0:6', 'EN-001:1.0:2', 'EN-001:1.0:1', 'EN-001:1.0:7', 'EN-001:1.0:4', 'EN-001:1.0:0', 'EN-001:1.0:3', 'EN-001:1.0:10', 'EN-001:1.0:9']
- covered_aspects: ['maximum consecutive working days of annual leave allowed without special approval']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragment 0 directly states the 10 consecutive working day limit and that longer periods require special approval, fully answering the question.'

**Expected evidence:**
- EN-001:1.0:5: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-07 — mexico-employee (expected: answerable)

**Question:** ¿Puedo usar brevemente el ordenador de la empresa para un asunto personal mientras trabajo en México?

**Expected answer summary:** Sí, el uso personal incidental puede permitirse cuando sea razonable, lícito y no interfiera con el trabajo ni infrinja otras normas de la empresa.
**Expected aspects:** ['Uso personal incidental permitido si es razonable, lícito y no interfiere con el trabajo']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Sí, el uso personal incidental de los recursos de la empresa puede estar permitido siempre que sea razonable, lícito y no interfiera con el trabajo ni infrinja otras normas de la empresa. Si tienes dudas sobre qué se considera un uso aceptable, debes consultar con el contacto correspondiente de TI o Recursos Humanos. Los fragmentos disponibles no mencionan ninguna distinción según el país o ubicación desde la que se trabaje, como México.

**Citations:**
- GLB-001 v1.0 — 6. Responsible use of company resources (`GLB-001:1.0:6`)

**Attempt 1** — query: '¿Puedo usar brevemente el ordenador de la empresa para un asunto personal mientras trabajo en México?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| GLB-001:1.0:6 | 0.3662 | 0.9972 |
| MX-002:1.0:8 | 0.3354 | 0.9931 |
| MX-002:1.0:2 | 0.4035 | 0.9927 |
| MX-002:1.0:12 | 0.4193 | 0.9918 |
| GLB-002:1.0:4 | 0.3941 | 0.9877 |
| GLB-001:1.0:12 | 0.4211 | 0.9738 |
| MX-001:1.1:11 | 0.4114 | 0.9702 |
| MX-001:1.1:2 | 0.3722 | 0.9696 |
| GLB-002:1.0:7 | 0.3775 | 0.8712 |
| MX-002:1.0:7 | 0.3796 | 0.8506 |

- kept: ['GLB-001:1.0:6', 'GLB-002:1.0:4']
- discarded: ['MX-002:1.0:8', 'MX-002:1.0:2', 'MX-002:1.0:12', 'GLB-001:1.0:12', 'MX-001:1.1:11', 'MX-001:1.1:2', 'GLB-002:1.0:7', 'MX-002:1.0:7']
- covered_aspects: ['General global policy on incidental personal use of company devices', 'Requirements for responsible use of corporate devices']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'GLB-001 section 6 directly addresses incidental personal use of company resources being permitted if reasonable, lawful, and non-disruptive, and GLB-002 clarifies device usage rules; no Mexico-specific exception applies, so these fragments fully answer the question.'

**Expected evidence:**
- GLB-001:1.0:6: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-08 — spain-manager (expected: answerable)

**Question:** Como manager en España, uno de mis colaboradores solicita un periodo de vacaciones y tiene saldo suficiente. ¿Eso implica que debo aprobarlo automáticamente, y qué pasos concretos tengo que seguir antes de decidir?

**Expected answer summary:** No. Tener saldo suficiente no implica aprobación automática: debo valorar el calendario del equipo, los periodos de actividad crítica y la cobertura de funciones esenciales (ES-001 §5). En concreto, debo comprobar las fechas solicitadas y la cobertura operativa, identificar posibles coincidencias con otras ausencias ya aprobadas, revisar las condiciones aplicables de ES-001/ES-002, y registrar mi decisión y su justificación en el sistema corporativo (ES-006 §3).
**Expected aspects:** ['El saldo suficiente no implica aprobación automática', 'Pasos concretos antes de decidir: fechas/cobertura, coincidencias con otras ausencias, condiciones aplicables, registro de la decisión']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** No, el saldo suficiente no implica aprobación automática. Según ES-001, la existencia de saldo suficiente no implica la aprobación automática de las fechas solicitadas, y hasta recibir confirmación las vacaciones se consideran pendientes.

Como manager, antes de decidir debes seguir estos pasos:
1. Comprobar las fechas solicitadas y la cobertura operativa del equipo.
2. Identificar posibles coincidencias con otras ausencias ya aprobadas.
3. Revisar las condiciones aplicables en ES-001 (o ES-002, según corresponda).
4. Registrar la decisión y su justificación operativa en el sistema corporativo.
5. Escalar a RR. HH. los casos que excedan tu ámbito de decisión.

Además, al evaluar la solicitud debes tener en cuenta el calendario del equipo, los periodos de actividad crítica y la cobertura de funciones esenciales, aplicando los criterios de ES-001, incluidos el preaviso ordinario de 15 días naturales y el límite ordinario de 15 días laborables consecutivos, salvo excepción autorizada. Debes valorar los compromisos del equipo, las sustituciones disponibles y los periodos de mayor carga de trabajo, con criterios consistentes y evitando decisiones arbitrarias.

Si la solicitud supera el límite ordinario de días consecutivos o requiere una excepción a la política, debes remitirla a RR. HH. España, ya que no puedes conceder por ti solo una excepción reservada a RR. HH. Si varias solicitudes coinciden y afectan a la cobertura del equipo, debes evaluar el impacto operativo, explorar alternativas, comunicar la decisión de forma clara y respetuosa, y consultar a RR. HH. España si el conflicto no puede resolverse de manera objetiva.

**Citations:**
- ES-001 v1.0 — 5. Aprobación y planificación del equipo (`ES-001:1.0:5`)
- ES-006 v1.0 — 4. Gestión de vacaciones (`ES-006:1.0:4`)
- ES-006 v1.0 — 3. Recepción y revisión de solicitudes (`ES-006:1.0:3`)
- ES-001 v1.0 — 6. Periodos consecutivos (`ES-001:1.0:6`)
- ES-006 v1.0 — 7. Solicitudes coincidentes y conflictos de cobertura (`ES-006:1.0:7`)

**Attempt 1** — query: 'Como manager en España, uno de mis colaboradores solicita un periodo de vacaciones y tiene saldo suficiente. ¿Eso implica que debo aprobarlo automáticamente, y qué pasos concretos tengo que seguir antes de decidir?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:5 | 0.2951 | 1.0000 |
| ES-001:1.0:4 | 0.3287 | 0.9999 |
| ES-006:1.0:4 | 0.2796 | 0.9997 |
| ES-001:1.0:8 | 0.3120 | 0.9997 |
| ES-006:1.0:3 | 0.3224 | 0.9988 |
| ES-006:1.0:8 | 0.3203 | 0.9987 |
| ES-001:1.0:9 | 0.3526 | 0.9958 |
| ES-001:1.0:6 | 0.3569 | 0.9940 |
| ES-006:1.0:7 | 0.3677 | 0.9930 |
| ES-005:1.0:3 | 0.3247 | 0.9922 |

- kept: ['ES-001:1.0:4', 'ES-001:1.0:5', 'ES-001:1.0:6', 'ES-006:1.0:3', 'ES-006:1.0:4', 'ES-006:1.0:7']
- discarded: ['ES-001:1.0:8', 'ES-006:1.0:8', 'ES-001:1.0:9', 'ES-005:1.0:3']
- covered_aspects: ['saldo suficiente no implica aprobación automática', 'criterios de aprobación: calendario del equipo, periodos críticos, cobertura', 'pasos concretos: comprobar fechas y cobertura, revisar coincidencias, revisar condiciones de ES-001, registrar decisión, escalar si corresponde', 'gestión de solicitudes coincidentes y conflictos de cobertura', 'límites ordinarios (preaviso 15 días, 15 días laborables consecutivos) y cuándo escalar a RR.HH.']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Los fragmentos de ES-001 y ES-006 cubren explícitamente que el saldo suficiente no implica aprobación automática y detallan los pasos concretos (comprobación de fechas, cobertura, coincidencias, registro, escalado) que el manager debe seguir antes de decidir.'

**Expected evidence:**
- ES-001:1.0:5: ever_retrieved=True in_final_context=True
- ES-006:1.0:3: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-09 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, si un gasto de viaje va a superar los límites ordinarios de la política, ¿qué tiene que haber ocurrido antes de que se considere autorizado, y qué debo comprobar yo al revisar el caso?

**Expected answer summary:** Debe existir una autorización excepcional previa, documentada en los canales corporativos correspondientes; no se presume concedida por el hecho de que el viaje ya esté aprobado o el gasto ya se haya realizado (ES-005 §9). Al revisar el caso, debo identificar el concepto, el importe, el motivo de la excepción, la autorización y los justificantes pertinentes, colaborando con Finanzas cuando afecte a condiciones de personal (ES-007 §8).
**Expected aspects:** ['La excepción debe ser previa y documentada, nunca presumida por la aprobación del viaje o el gasto ya realizado', 'RR. HH. debe identificar concepto, importe, motivo, autorización y justificantes al revisar el caso']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Para que un gasto que supera los límites ordinarios se considere autorizado, debe existir una autorización excepcional previa, obtenida antes de que se realice el gasto, conforme al procedimiento interno correspondiente de la política ES-005. Esta excepción debe quedar documentada en los canales corporativos correspondientes; no se presume concedida por el hecho de que el viaje haya sido aprobado previamente ni por el hecho de que el gasto ya se haya realizado.

Como responsable de RR. HH. al revisar el caso, debes:
1. Identificar la política vigente y la regla ordinaria afectada, y confirmar que la solicitud pertenece al ámbito de España.
2. Revisar únicamente los antecedentes administrativos necesarios y verificar la justificación y los efectos operativos aportados, sin solicitar información sensible innecesaria.
3. Comprobar si existe un requisito legal o contractual que deba prevalecer sobre la política interna.
4. Determinar el nivel de autorización aplicable y documentar el resultado, basando la decisión en criterios objetivos y comparables, sin utilizar características personales protegidas ni información médica como criterios de conveniencia empresarial.
5. Específicamente para el gasto excepcional, identificar el concepto, importe, motivo de la excepción, autorización y justificantes pertinentes, colaborando con Finanzas cuando el caso afecte a condiciones de personal (aunque la validación económica se tramita por el circuito corporativo correspondiente). Ten en cuenta que los límites máximos de la política no se interpretan como importes garantizados.

**Citations:**
- ES-005 v1.0 — 3. Autorización y planificación del viaje (`ES-005:1.0:3`)
- ES-005 v1.0 — 9. Excepciones y superación de límites (`ES-005:1.0:9`)
- ES-007 v1.0 — 3. Principios de revisión (`ES-007:1.0:3`)
- ES-007 v1.0 — 8. Gastos y desplazamientos excepcionales (`ES-007:1.0:8`)

**Attempt 1** — query: 'Como responsable de RR. HH. en España, si un gasto de viaje va a superar los límites ordinarios de la política, ¿qué tiene que haber ocurrido antes de que se considere autorizado, y qué debo comprobar yo al revisar el caso?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:3 | 0.3259 | 0.9998 |
| ES-007:1.0:4 | 0.3651 | 0.9998 |
| ES-001:1.0:8 | 0.3683 | 0.9997 |
| ES-005:1.0:9 | 0.2992 | 0.9995 |
| ES-007:1.0:3 | 0.3293 | 0.9995 |
| ES-007:1.0:8 | 0.2512 | 0.9994 |
| ES-006:1.0:4 | 0.3710 | 0.9991 |
| ES-006:1.0:8 | 0.3307 | 0.9988 |
| ES-005:1.0:6 | 0.3727 | 0.9986 |
| ES-005:1.0:8 | 0.3846 | 0.9975 |

- kept: ['ES-005:1.0:3', 'ES-005:1.0:6', 'ES-005:1.0:8', 'ES-005:1.0:9', 'ES-007:1.0:3', 'ES-007:1.0:8']
- discarded: ['ES-007:1.0:4', 'ES-001:1.0:8', 'ES-006:1.0:4', 'ES-006:1.0:8']
- covered_aspects: ['requirement for prior exceptional authorization before exceeding travel expense limits', 'what must have occurred before considered authorized (prior authorization, documented via corporate channels, not presumed by trip approval or expense already incurred)', 'what HR should check when reviewing: concept, amount, reason for exception, authorization, supporting documents', 'general review principles for HR before resolving an exception (identify policy, verify justification, operational effects, legal/contractual requirements, authorization level, documentation)', 'collaboration with Finance for economic validation']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragments ES-005 §3/9/6/8 establish that prior exceptional authorization is required and must be documented before an expense exceeding limits is considered authorized, while ES-007 §3 and §8 detail exactly what HR must verify when reviewing such a case (concept, amount, justification, authorization, legal requirements), together fully answering both parts of the question.'

**Expected evidence:**
- ES-005:1.0:9: ever_retrieved=True in_final_context=True
- ES-007:1.0:8: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-10 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, si un empleado solicita de forma recurrente teletrabajar un cuarto día cada semana además del régimen habitual de tres días, ¿qué tengo que comprobar antes de decidir, y una concesión puntual cambiaría su régimen habitual de forma permanente?

**Expected answer summary:** No, una excepción concedida para una semana no modifica automáticamente el régimen habitual ni crea una autorización permanente (ES-003 §6). Antes de decidir sobre una solicitud que supere el régimen ordinario de tres días semanales, debo comprobar la elegibilidad del puesto, las condiciones individuales aplicables, la valoración del responsable directo y las necesidades de coordinación del equipo (ES-007 §6).
**Expected aspects:** ['Una concesión puntual no modifica el régimen habitual ni crea una autorización permanente', 'RR. HH. debe comprobar elegibilidad del puesto, condiciones individuales, valoración del responsable y necesidades de coordinación']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Antes de decidir sobre una solicitud recurrente de un cuarto día de teletrabajo, como responsable de RR. HH. debe seguir el procedimiento de excepción aplicable: la persona interesada debe plantearlo con antelación razonable a su responsable [0]. Además, al tratarse de una solicitud superior al régimen ordinario de 3 días semanales, requiere revisión excepcional, en la que RR. HH. debe comprobar la elegibilidad del puesto, las condiciones individuales aplicables, la valoración del responsable y las necesidades de coordinación [1]. De forma más general, antes de resolver cualquier excepción, RR. HH. debe identificar la política vigente y la regla ordinaria afectada, confirmar que la solicitud pertenece al ámbito de España, revisar únicamente los antecedentes administrativos necesarios, verificar la justificación y los efectos operativos aportados sin solicitar información sensible innecesaria, comprobar si existe un requisito legal o contractual que deba prevalecer sobre la política interna, y determinar el nivel de autorización aplicable y documentar el resultado, basándose en criterios objetivos y comparables, sin usar características personales protegidas ni información médica [2]. En cuanto a si una concesión puntual cambia el régimen habitual de forma permanente: no. Una excepción concedida para una semana no modifica automáticamente el régimen habitual ni crea una autorización permanente [0]. También debe tenerse en cuenta que un responsable no debe comunicar una excepción como aprobada antes de que se haya completado el proceso correspondiente [0].

**Citations:**
- ES-003 v1.0 — 6. Teletrabajo adicional y excepciones (`ES-003:1.0:7`)
- ES-007 v1.0 — 6. Excepciones de teletrabajo y flexibilidad (`ES-007:1.0:6`)
- ES-007 v1.0 — 3. Principios de revisión (`ES-007:1.0:3`)

**Attempt 1** — query: 'Como responsable de RR. HH. en España, si un empleado solicita de forma recurrente teletrabajar un cuarto día cada semana además del régimen habitual de tres días, ¿qué tengo que comprobar antes de decidir, y una concesión puntual cambiaría su régimen habitual de forma permanente?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-003:1.0:7 | 0.2082 | 0.9999 |
| ES-007:1.0:6 | 0.2485 | 0.9997 |
| ES-001:1.0:8 | 0.3134 | 0.9989 |
| ES-007:1.0:3 | 0.3592 | 0.9988 |
| ES-007:1.0:4 | 0.3171 | 0.9985 |
| ES-003:1.0:3 | 0.3290 | 0.9979 |
| ES-006:1.0:4 | 0.3660 | 0.9954 |
| ES-003:1.0:6 | 0.3674 | 0.9845 |
| ES-003:1.0:5 | 0.3238 | 0.9411 |
| ES-006:1.0:8 | 0.3214 | 0.9169 |

- kept: ['ES-003:1.0:7', 'ES-007:1.0:3', 'ES-007:1.0:6']
- discarded: ['ES-001:1.0:8', 'ES-007:1.0:4', 'ES-003:1.0:3', 'ES-006:1.0:4', 'ES-003:1.0:6', 'ES-003:1.0:5', 'ES-006:1.0:8']
- covered_aspects: ['procedure for requesting a 4th telework day exception', 'that a one-time grant does not permanently change the regular regime', 'general review principles RR.HH. must verify before resolving an exception (applicable rule, scope, justification, operational effects, legal/contractual requirements, authorization level)', 'related excepción escalation requirements from ES-007']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'ES-003 §6 directly states a one-off exception does not alter the habitual regime, and ES-007 §3 and §6 give the concrete checklist RR.HH. must verify before deciding on recurring telework exceptions, together covering both parts of the question.'

**Expected evidence:**
- ES-003:1.0:7: ever_retrieved=True in_final_context=True
- ES-007:1.0:6: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-11 — spain-employee (expected: answerable)

**Question:** Si teletrabajo en España, ¿con qué tipo de equipo debo hacerlo, y puedo usar mi propio ordenador personal si tengo activada la autenticación en dos pasos?

**Expected answer summary:** Debo usar dispositivos corporativos y herramientas autorizadas; usar un portátil o una conexión segura no sustituye esa exigencia (ES-003 §7). Un dispositivo personal no está permitido para acceder a aplicaciones o datos corporativos, salvo que exista una excepción específica documentada y aprobada previamente por Seguridad de la Información — tener activada la autenticación en dos pasos no sustituye esa aprobación (GLB-002 §4).
**Expected aspects:** ['El teletrabajo requiere dispositivos corporativos y herramientas autorizadas', 'Un dispositivo personal solo se permite con una excepción documentada y aprobada previamente por Seguridad de la Información']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Si teletrabaja en España, debe hacerlo con dispositivos corporativos y herramientas autorizadas, de acuerdo con la política GLB-002 — Information Security Policy, protegiendo el acceso a los sistemas, evitando que terceros vean información confidencial, utilizando los mecanismos corporativos de autenticación y comunicando los incidentes por los canales establecidos. En cuanto a usar su propio ordenador personal: no está permitido, ya que la ayuda para equipamiento de teletrabajo no autoriza a utilizar dispositivos personales o servicios no aprobados para acceder a información corporativa, independientemente de tener activada la autenticación en dos pasos (esta medida no se menciona como excepción en los fragmentos disponibles).

**Citations:**
- ES-003 v1.0 — 7. Equipamiento y seguridad de la información (`ES-003:1.0:8`)
- ES-004 v1.0 — 8. Ayuda para equipamiento de teletrabajo (`ES-004:1.0:10`)

**Attempt 1** — query: 'Si teletrabajo en España, ¿con qué tipo de equipo debo hacerlo, y puedo usar mi propio ordenador personal si tengo activada la autenticación en dos pasos?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| GLB-002:1.0:7 | 0.3338 | 0.9977 |
| GLB-002:1.0:11 | 0.4114 | 0.9894 |
| ES-003:1.0:8 | 0.3886 | 0.9884 |
| ES-004:1.0:10 | 0.4352 | 0.9849 |
| ES-003:1.0:12 | 0.4161 | 0.9614 |
| ES-005:1.0:10 | 0.3879 | 0.9525 |
| ES-005:1.0:12 | 0.4346 | 0.9368 |
| ES-003:1.0:5 | 0.4121 | 0.7673 |
| ES-004:1.0:9 | 0.4082 | 0.6957 |
| ES-003:1.0:11 | 0.4113 | 0.0415 |

- kept: ['ES-003:1.0:8', 'ES-004:1.0:10']
- discarded: ['GLB-002:1.0:7', 'GLB-002:1.0:11', 'ES-003:1.0:12', 'ES-005:1.0:10', 'ES-005:1.0:12', 'ES-003:1.0:5', 'ES-004:1.0:9', 'ES-003:1.0:11']
- covered_aspects: ['type of equipment required for teleworking in Spain (corporate devices and authorized tools per GLB-002)', 'whether personal computer can be used (not allowed, as corporate authentication mechanisms are required, not personal 2FA)', 'confirmation that security measures like 2FA do not substitute organizational/device authorization']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragments [2] and [3] directly state that remote work must use corporate devices and authorized tools per GLB-002, and explicitly clarify that personal devices or unapproved services (even with security measures) are not authorized substitutes, fully answering both parts of the question.'

**Expected evidence:**
- ES-003:1.0:8: ever_retrieved=True in_final_context=True
- GLB-002:1.0:4: ever_retrieved=False in_final_context=False

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-12 — spain-manager (expected: answerable)

**Question:** Como manager en España, un colaborador me comunica, sin haber avisado con antelación, que tiene que ausentarse por una emergencia familiar imprevista. ¿Estaba obligado a avisar con antelación en este caso, puedo exigirle que me explique el motivo médico o clínico, y qué debo hacer yo en ese momento?

**Expected answer summary:** No estaba obligado a avisar con antelación: no se exige una solicitud anticipada cuando la naturaleza de la emergencia lo impide (ES-002 §7). Tampoco puedo exigirle que explique el motivo médico o clínico: no debo pedir diagnósticos, informes clínicos ni explicaciones médicas detalladas. Como manager, debo confirmar la recepción de la comunicación y organizar la cobertura operativa razonable, informando a RR. HH. si resulta necesario para la tramitación administrativa (ES-006 §6).
**Expected aspects:** ['No existía obligación de avisar con antelación, dado que la naturaleza de la emergencia lo impedía', 'El manager no debe pedir diagnósticos ni detalles clínicos', 'El manager debe confirmar la comunicación y organizar la cobertura, informando a RR. HH. si es necesario']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** No, no estaba obligado a avisar con antelación: ante una emergencia familiar imprevista, la prioridad es que la persona comunique la situación tan pronto como sea razonablemente posible, y no se exige una solicitud anticipada cuando la naturaleza de la emergencia lo impida [0]. Esto es coherente con el principio general de que, si la ausencia es imprevista, basta con informar al responsable directo tan pronto como resulte razonablemente posible [1].

No, no puede exigirle explicaciones médicas o clínicas: ante ausencias imprevistas, el manager no debe pedir diagnósticos, informes clínicos ni explicaciones médicas detalladas, ya que los justificantes y documentos sensibles se gestionan exclusivamente mediante los canales autorizados de RR. HH. [2].

Como manager, en ese momento debe: confirmar la recepción de la comunicación y organizar la cobertura operativa razonable, informando a RR. HH. si resulta necesario para la tramitación administrativa correspondiente [2]. También debe organizar la cobertura operativa sin solicitar información privada innecesaria [0], y la información que comparta con el resto del equipo debe limitarse a lo necesario para organizar el trabajo, sin revelar motivos privados de la ausencia [2]. Tenga en cuenta que será Recursos Humanos quien evalúe el tipo de permiso o ausencia aplicable y comunique los requisitos administrativos pertinentes, y que la existencia de la emergencia no implica por sí sola el descuento de días de vacaciones ni determina una duración o condición retributiva específica [0].

**Citations:**
- ES-002 v1.0 — 7. Emergencias familiares (`ES-002:1.0:7`)
- ES-002 v1.0 — 3. Principios generales de comunicación (`ES-002:1.0:3`)
- ES-006 v1.0 — 6. Ausencias imprevistas y enfermedad (`ES-006:1.0:6`)

**Attempt 1** — query: 'Como manager en España, un colaborador me comunica, sin haber avisado con antelación, que tiene que ausentarse por una emergencia familiar imprevista. ¿Estaba obligado a avisar con antelación en este caso, puedo exigirle que me explique el motivo médico o clínico, y qué debo hacer yo en ese momento?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-002:1.0:7 | 0.2919 | 0.9988 |
| ES-002:1.0:3 | 0.2971 | 0.9987 |
| ES-002:1.0:5 | 0.3039 | 0.9977 |
| ES-006:1.0:6 | 0.3032 | 0.9975 |
| ES-002:1.0:6 | 0.3658 | 0.9971 |
| ES-001:1.0:8 | 0.3554 | 0.9922 |
| ES-006:1.0:2 | 0.3614 | 0.9912 |
| ES-002:1.0:9 | 0.3620 | 0.9630 |
| ES-006:1.0:8 | 0.3627 | 0.7134 |
| ES-005:1.0:9 | 0.3624 | 0.0096 |

- kept: ['ES-002:1.0:3', 'ES-002:1.0:7', 'ES-006:1.0:6']
- discarded: ['ES-002:1.0:5', 'ES-002:1.0:6', 'ES-001:1.0:8', 'ES-006:1.0:2', 'ES-002:1.0:9', 'ES-006:1.0:8', 'ES-005:1.0:9']
- covered_aspects: ['No se exige aviso previo en emergencias familiares imprevistas', 'No se puede exigir explicación médica o clínica detallada', 'Qué debe hacer el manager: confirmar recepción, organizar cobertura, informar a RR.HH. si procede, sin pedir información privada innecesaria']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Los fragmentos 0 y 1 confirman que no se exige aviso previo ante emergencias imprevistas, y el fragmento 3 (junto con el 0) detalla que el manager no debe pedir diagnósticos ni detalles médicos y debe limitarse a confirmar la comunicación y organizar la cobertura operativa, cubriendo todos los aspectos de la pregunta.'

**Expected evidence:**
- ES-002:1.0:7: ever_retrieved=True in_final_context=True
- ES-006:1.0:6: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-13 — england-employee (expected: answerable)

**Question:** In England, if I need to request annual leave with less notice than the ordinary 14 calendar days because of a specific personal circumstance, could that still be considered, and who is responsible for deciding on an exception like that?

**Expected answer summary:** Short-notice requests may be considered where circumstances justify them, although the ordinary notice period is an internal planning expectation and does not override statutory rights (EN-001 §4). England HR is responsible for interpreting the policy and assessing exceptions, together with the relevant line manager where appropriate, and any exception must be documented (EN-001 §12).
**Expected aspects:** ['Short-notice requests may be considered when circumstances justify them', 'England HR, together with the line manager, is responsible for assessing and documenting any exception']

**Abstained:** False  ·  **Retrievals:** 3

**Answer:** Yes. According to the England annual leave policy, short-notice requests may be considered where circumstances justify them, and the ordinary 14-day notice period is only an internal planning expectation rather than an absolute rule. As for who decides on exceptions, England HR is responsible for interpreting the policy and assessing exceptions, together with the relevant line manager where appropriate. Any exception must be documented and must not reduce statutory rights.

**Citations:**
- EN-001 v1.0 — 4. Requesting annual leave (`EN-001:1.0:4`)
- EN-001 v1.0 — 12. Exceptions, interpretation and related policies (`EN-001:1.0:12`)

**Attempt 1** — query: 'In England, if I need to request annual leave with less notice than the ordinary 14 calendar days because of a specific personal circumstance, could that still be considered, and who is responsible for deciding on an exception like that?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:5 | 0.2808 | 0.9989 |
| EN-001:1.0:4 | 0.3605 | 0.9979 |
| EN-001:1.0:1 | 0.3210 | 0.9964 |
| EN-001:1.0:9 | 0.3348 | 0.9923 |
| EN-001:1.0:7 | 0.3092 | 0.9870 |
| EN-001:1.0:6 | 0.3762 | 0.7073 |
| EN-001:1.0:2 | 0.3730 | 0.5433 |
| EN-001:1.0:3 | 0.3803 | 0.3716 |
| EN-001:1.0:10 | 0.3590 | 0.3364 |
| EN-001:1.0:8 | 0.4140 | 0.2215 |

- kept: ['EN-001:1.0:4']
- discarded: ['EN-001:1.0:5', 'EN-001:1.0:1', 'EN-001:1.0:9', 'EN-001:1.0:7', 'EN-001:1.0:6', 'EN-001:1.0:2', 'EN-001:1.0:3', 'EN-001:1.0:10', 'EN-001:1.0:8']
- covered_aspects: ['ordinary 14-day notice period exists as internal planning expectation', 'short-notice requests may be considered where circumstances justify them']
- missing_aspects: ['who specifically decides/approves a short-notice exception (confirm it is the line manager alone or requires HR involvement)', 'what process or criteria apply when evaluating short-notice leave requests']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Fragment [1] confirms short-notice requests can be considered but does not clearly specify who has decision authority for approving such an exception beyond general line manager review mentioned for standard requests.'

**Attempt 2** — query: 'short-notice annual leave exception approval process England line manager HR criteria'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:5 | 0.2952 | 0.9997 |
| EN-001:1.0:4 | 0.3755 | 0.9992 |
| EN-001:1.0:12 | 0.3907 | 0.9918 |
| EN-001:1.0:7 | 0.3981 | 0.9808 |
| EN-001:1.0:1 | 0.4152 | 0.9785 |
| EN-001:1.0:9 | 0.4186 | 0.9633 |
| EN-001:1.0:0 | 0.4181 | 0.9470 |
| EN-001:1.0:8 | 0.4594 | 0.5110 |
| EN-001:1.0:11 | 0.4326 | 0.5051 |
| GLB-001:1.0:11 | 0.4632 | 0.0185 |

- kept: ['EN-001:1.0:12', 'EN-001:1.0:4']
- discarded: ['EN-001:1.0:5', 'EN-001:1.0:7', 'EN-001:1.0:1', 'EN-001:1.0:9', 'EN-001:1.0:0', 'EN-001:1.0:8', 'EN-001:1.0:11', 'GLB-001:1.0:11']
- covered_aspects: ['ordinary 14-day notice period and its status as a planning expectation', 'short-notice requests may be considered where circumstances justify them', 'line manager reviews leave requests based on staffing/business needs', 'England HR and line manager role in interpreting policy and assessing exceptions']
- missing_aspects: ["explicit confirmation of who specifically decides short-notice requests (line manager vs England HR) for the day-to-day request process, as opposed to general 'exceptions' language in section 12 which may refer to broader policy exceptions rather than routine short-notice leave approval"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment 0 confirms short-notice requests may be considered but doesn't clearly state who decides, while fragment 2 discusses exceptions generally via England HR and line manager, leaving some ambiguity about whether that applies specifically to short-notice leave decisions."

**Attempt 3** — query: 'who approves short-notice annual leave requests England line manager versus HR decision authority day-to-day'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:5 | 0.3246 | 0.9993 |
| EN-001:1.0:4 | 0.3934 | 0.9967 |
| EN-001:1.0:12 | 0.4369 | 0.9875 |
| EN-001:1.0:7 | 0.4104 | 0.9849 |
| EN-001:1.0:1 | 0.4417 | 0.9811 |
| EN-001:1.0:9 | 0.4211 | 0.9737 |
| EN-001:1.0:0 | 0.4869 | 0.9341 |
| EN-001:1.0:11 | 0.4688 | 0.8672 |
| EN-001:1.0:3 | 0.4439 | 0.5965 |
| EN-001:1.0:6 | 0.4734 | 0.4958 |

- kept: ['EN-001:1.0:12', 'EN-001:1.0:4']
- discarded: ['EN-001:1.0:5', 'EN-001:1.0:7', 'EN-001:1.0:1', 'EN-001:1.0:9', 'EN-001:1.0:0', 'EN-001:1.0:11', 'EN-001:1.0:3', 'EN-001:1.0:6']
- covered_aspects: ['Short-notice requests may be considered where circumstances justify them', 'Line manager reviews/approves leave requests generally', 'Exceptions must be documented and assessed by England HR and the relevant line manager']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragment 0 confirms short-notice requests can be considered, and fragment 1 establishes that England HR, together with the line manager where appropriate, is responsible for assessing exceptions to the policy.'

**Expected evidence:**
- EN-001:1.0:4: ever_retrieved=True in_final_context=True
- EN-001:1.0:12: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-14 — mexico-employee (expected: answerable)

**Question:** Antes de usar una herramienta de IA ya aprobada por la empresa para generar un primer borrador de un informe que incluye datos internos de rendimiento de mi equipo en México, ¿qué debo comprobar sobre ese tipo de información, y qué debo hacer con el contenido que genere la herramienta antes de compartirlo?

**Expected answer summary:** Debo comprobar que la información interna puede introducirse en esa herramienta concreta: no debe introducirse información interna en servicios no aprobados para ese uso, salvo que Seguridad de la Información haya autorizado expresamente esa categoría (GLB-002 §6). Antes de compartir el contenido generado, debo revisarlo en cuanto a exactitud, adecuación, confidencialidad y posible sesgo, ya que sigo siendo responsable de mis decisiones profesionales y de los resultados de mi trabajo (GLB-001 §7).
**Expected aspects:** ['La información interna solo puede introducirse en una herramienta aprobada para ese uso, o con autorización expresa de Seguridad de la Información', 'El contenido generado debe revisarse por exactitud, adecuación, confidencialidad y posible sesgo antes de compartirse']

**Abstained:** False  ·  **Retrievals:** 1

**Answer:** Antes de introducir los datos internos de rendimiento de tu equipo en la herramienta de IA, debes comprobar que esa información —clasificada como 'Internal'— puede usarse en ese servicio: solo se puede introducir información Internal en servicios no aprobados si Seguridad de la Información lo ha autorizado expresamente, y en el caso de un tool ya aprobado, la aprobación del tool no implica por sí sola autorización para divulgar cualquier categoría de información en él, por lo que conviene verificar que ese uso específico (datos internos de rendimiento) está cubierto por la aprobación. Una vez generado el borrador, debes revisar el contenido generado por la IA antes de usarlo o compartirlo, verificando su precisión, idoneidad, confidencialidad y posibles sesgos, ya que sigues siendo responsable de tus decisiones profesionales y de los productos de trabajo resultantes.

**Citations:**
- GLB-001 v1.0 — 7. Artificial intelligence and automated tools (`GLB-001:1.0:7`)
- GLB-002 v1.0 — 6. Use of artificial intelligence tools (`GLB-002:1.0:6`)

**Attempt 1** — query: 'Antes de usar una herramienta de IA ya aprobada por la empresa para generar un primer borrador de un informe que incluye datos internos de rendimiento de mi equipo en México, ¿qué debo comprobar sobre ese tipo de información, y qué debo hacer con el contenido que genere la herramienta antes de compartirlo?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| GLB-001:1.0:7 | 0.3709 | 0.9990 |
| GLB-002:1.0:6 | 0.3621 | 0.9987 |
| GLB-002:1.0:5 | 0.4376 | 0.9827 |
| MX-002:1.0:12 | 0.4634 | 0.9631 |
| GLB-001:1.0:6 | 0.4429 | 0.9605 |
| MX-002:1.0:9 | 0.4582 | 0.1549 |
| GLB-002:1.0:4 | 0.4787 | 0.0645 |
| MX-002:1.0:8 | 0.4143 | 0.0505 |
| GLB-002:1.0:8 | 0.4709 | 0.0200 |
| MX-001:1.1:8 | 0.4644 | 0.0008 |

- kept: ['GLB-001:1.0:7', 'GLB-002:1.0:6']
- discarded: ['GLB-002:1.0:5', 'MX-002:1.0:12', 'GLB-001:1.0:6', 'MX-002:1.0:9', 'GLB-002:1.0:4', 'MX-002:1.0:8', 'GLB-002:1.0:8', 'MX-001:1.1:8']
- covered_aspects: ["Need to verify classification/type of information allowed before entering into AI tool (approval of tool doesn't cover all data categories, and Internal info requires InfoSec authorization unless already approved)", 'Requirement to review AI-generated output for accuracy, appropriateness, confidentiality, bias before use or sharing', 'Employee responsibility for professional decisions/work product after using AI output']
- missing_aspects: []
- grader route: sufficient  ·  effective route: sufficient  ·  rationale: 'Fragments 0 and 1 together specify that even with an approved AI tool, employees must check whether the specific data category (here, internal team performance data) is authorized for that tool, and that any AI-generated output must be reviewed for accuracy, confidentiality and bias before being relied upon or shared, fully answering both parts of the question.'

**Expected evidence:**
- GLB-001:1.0:7: ever_retrieved=True in_final_context=True
- GLB-002:1.0:6: ever_retrieved=True in_final_context=True

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-15 — spain-employee (expected: abstain)

**Question:** Hace dos semanas tuve una comida de representación con un cliente en Madrid dentro de un viaje de trabajo. ¿Qué necesito para que ese gasto sea reembolsable, y ha sido ya aprobado y reembolsado mi gasto concreto?

**Expected answer summary:** —
**Expected aspects:** ['Cubierto en el corpus: requisitos generales de los gastos de representación (autorización previa específica, finalidad profesional identificable, documentación justificativa)', 'No cubierto: el estado real (aprobado/reembolsado o no) de este gasto concreto']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Hace dos semanas tuve una comida de representación con un cliente en Madrid dentro de un viaje de trabajo. ¿Qué necesito para que ese gasto sea reembolsable, y ha sido ya aprobado y reembolsado mi gasto concreto?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:7 | 0.2247 | 0.9990 |
| ES-005:1.0:8 | 0.3554 | 0.9968 |
| ES-005:1.0:1 | 0.4070 | 0.9966 |
| ES-005:1.0:5 | 0.3547 | 0.9953 |
| ES-004:1.0:4 | 0.4486 | 0.9914 |
| ES-005:1.0:6 | 0.3479 | 0.9901 |
| ES-005:1.0:9 | 0.3800 | 0.9830 |
| ES-005:1.0:4 | 0.3992 | 0.9604 |
| ES-004:1.0:7 | 0.3766 | 0.8899 |
| ES-005:1.0:3 | 0.3649 | 0.8830 |

- kept: ['ES-005:1.0:7', 'ES-005:1.0:8']
- discarded: ['ES-005:1.0:1', 'ES-005:1.0:5', 'ES-004:1.0:4', 'ES-005:1.0:6', 'ES-005:1.0:9', 'ES-005:1.0:4', 'ES-004:1.0:7', 'ES-005:1.0:3']
- covered_aspects: ['Requisitos generales para gastos de representación (autorización previa específica, finalidad profesional, documentación justificativa)', 'Plazo y procedimiento para presentar justificantes de gasto']
- missing_aspects: ['Estado concreto de aprobación/reembolso del gasto específico del usuario (dato individual, no está en la política general)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos explican claramente los requisitos generales para que un gasto de representación sea reembolsable, pero no contienen información sobre el estado real de la solicitud individual del usuario, que requeriría consultar el sistema de gestión de gastos.'

**Attempt 2** — query: 'Requisitos de política para reembolso de comidas de representación con clientes en viajes de negocio'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:7 | 0.3023 | 0.9990 |
| ES-004:1.0:7 | 0.4294 | 0.8986 |
| ES-005:1.0:11 | 0.4100 | 0.7726 |
| ES-005:1.0:1 | 0.3532 | 0.7459 |
| ES-005:1.0:8 | 0.4572 | 0.6779 |
| ES-005:1.0:6 | 0.4415 | 0.6580 |
| ES-005:1.0:5 | 0.4568 | 0.4745 |
| ES-005:1.0:3 | 0.4172 | 0.3623 |
| ES-005:1.0:4 | 0.4671 | 0.1992 |
| ES-005:1.0:9 | 0.4579 | 0.1837 |

- kept: ['ES-005:1.0:11', 'ES-005:1.0:7', 'ES-005:1.0:8']
- discarded: ['ES-004:1.0:7', 'ES-005:1.0:1', 'ES-005:1.0:6', 'ES-005:1.0:5', 'ES-005:1.0:3', 'ES-005:1.0:4', 'ES-005:1.0:9']
- covered_aspects: ['Requisitos generales para gastos de representación (autorización previa específica, finalidad profesional, documentación justificativa)', 'Plazo y procedimiento de presentación de justificantes', 'Alcance de Policy Consultant respecto a consultas sobre gastos personales concretos']
- missing_aspects: ['Estado real de aprobación del gasto de representación concreto del empleado', 'Confirmación de si el reembolso específico ya fue procesado o pagado']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos cubren bien los requisitos generales para que un gasto de representación sea reembolsable, pero el estado concreto de aprobación/reembolso del gasto particular del empleado no está disponible en estos documentos, que son de política general, no registros personales.'

**Attempt 3** — query: 'Estado de aprobación y pago de reembolso de gasto de representación o comida con cliente - consulta de solicitud individual del empleado'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-005:1.0:7 | 0.3290 | 0.9981 |
| ES-005:1.0:8 | 0.4224 | 0.9901 |
| ES-004:1.0:12 | 0.4332 | 0.9897 |
| ES-005:1.0:11 | 0.4584 | 0.9626 |
| ES-005:1.0:1 | 0.4645 | 0.9554 |
| ES-004:1.0:4 | 0.4192 | 0.8372 |
| ES-001:1.0:8 | 0.4703 | 0.7853 |
| ES-004:1.0:7 | 0.4289 | 0.1774 |
| ES-005:1.0:3 | 0.4473 | 0.1351 |
| ES-001:1.0:5 | 0.4509 | 0.1103 |

- kept: ['ES-005:1.0:11', 'ES-005:1.0:3', 'ES-005:1.0:7', 'ES-005:1.0:8']
- discarded: ['ES-004:1.0:12', 'ES-005:1.0:1', 'ES-004:1.0:4', 'ES-001:1.0:8', 'ES-004:1.0:7', 'ES-001:1.0:5']
- covered_aspects: ['requisitos para gastos de representación (autorización previa específica, finalidad profesional, documentación justificativa)', 'plazo y procedimiento para presentar justificantes', 'aclaración de que Policy Consultant no gestiona gastos ni reembolsos individuales']
- missing_aspects: ['estado concreto de aprobación del gasto de comida de representación realizado', 'confirmación de si el reembolso específico ya se ha procesado']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos cubren bien los requisitos generales para que un gasto de representación sea reembolsable, pero no proporcionan ni pueden proporcionar el estado real de aprobación/reembolso del gasto personal concreto, que la política indica que debe consultarse en otro sistema.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-16 — england-employee (expected: abstain)

**Question:** I'm expecting a child and will need to be away from my role in England for a while. What family-related leave categories might apply to me, and exactly how long would I personally be entitled to be off in my case?

**Expected answer summary:** —
**Expected aspects:** ["Covered in the corpus: statutory family-related leave categories exist (maternity, paternity, adoption, shared parental, dependants' emergency leave, etc.), with HR determining eligibility and documentation under current law", "Not covered: this employee's exact personal entitlement and duration for their specific case"]

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** Not enough evidence was found to answer with confidence.

**Citations:** none

**Attempt 1** — query: "I'm expecting a child and will need to be away from my role in England for a while. What family-related leave categories might apply to me, and exactly how long would I personally be entitled to be off in my case?"

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:9 | 0.3614 | 0.9985 |
| EN-001:1.0:5 | 0.3663 | 0.9957 |
| EN-001:1.0:1 | 0.3634 | 0.9822 |
| EN-001:1.0:0 | 0.4614 | 0.9809 |
| EN-001:1.0:7 | 0.4478 | 0.9584 |
| EN-001:1.0:12 | 0.4684 | 0.9226 |
| EN-001:1.0:2 | 0.4244 | 0.6204 |
| EN-001:1.0:10 | 0.4336 | 0.1166 |
| EN-001:1.0:6 | 0.4463 | 0.0481 |
| EN-001:1.0:4 | 0.4862 | 0.0150 |

- kept: ['EN-001:1.0:9']
- discarded: ['EN-001:1.0:5', 'EN-001:1.0:1', 'EN-001:1.0:0', 'EN-001:1.0:7', 'EN-001:1.0:12', 'EN-001:1.0:2', 'EN-001:1.0:10', 'EN-001:1.0:6', 'EN-001:1.0:4']
- covered_aspects: ["lists possible family-related leave categories (maternity, paternity, adoption, shared parental, parental bereavement, dependants' emergency leave)", 'notes that eligibility, documentation and pay arrangements depend on individual circumstances and are determined by HR under applicable statutory rules']
- missing_aspects: ['specific statutory duration entitlements for maternity/parental leave', "how to determine which category applies to this specific employee's situation", 'personalized calculation of exact time off based on individual circumstances']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment 0 names the relevant leave categories and explains eligibility is determined by HR per statutory rules, but no fragment gives actual duration entitlements or applies them to the individual's specific case."

**Attempt 2** — query: 'Maternity leave and parental leave duration England statutory entitlement weeks eligibility criteria'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:9 | 0.3436 | 0.9942 |
| EN-001:1.0:5 | 0.3942 | 0.9836 |
| EN-001:1.0:1 | 0.4313 | 0.9809 |
| EN-001:1.0:2 | 0.4945 | 0.7472 |
| EN-001:1.0:12 | 0.4920 | 0.7364 |
| EN-001:1.0:0 | 0.4886 | 0.5446 |
| EN-001:1.0:7 | 0.5306 | 0.0713 |
| EN-001:1.0:3 | 0.5381 | 0.0490 |
| EN-001:1.0:10 | 0.4880 | 0.0194 |
| EN-001:1.0:6 | 0.5115 | 0.0172 |

- kept: ['EN-001:1.0:9']
- discarded: ['EN-001:1.0:5', 'EN-001:1.0:1', 'EN-001:1.0:2', 'EN-001:1.0:12', 'EN-001:1.0:0', 'EN-001:1.0:7', 'EN-001:1.0:3', 'EN-001:1.0:10', 'EN-001:1.0:6']
- covered_aspects: ['categories of family-related leave (maternity, paternity, adoption, shared parental, etc.)', 'notification process and that company-paid personal days are separate from statutory entitlements', 'HR determines eligibility, documentation and pay arrangements']
- missing_aspects: ['specific statutory duration/length of maternity or other family leave entitlement', "how eligibility and duration apply to this individual's personal circumstances", "exact entitlement calculation based on employee's situation"]
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment 0 identifies the relevant leave categories and notes HR determines specifics, but no fragment states actual durations or how the entitlement applies to this specific employee's case."

**Attempt 3** — query: 'England maternity leave entitlement 52 weeks Ordinary and Additional Maternity Leave eligibility requirements calculation'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:9 | 0.3740 | 0.9917 |
| EN-001:1.0:1 | 0.4272 | 0.9050 |
| EN-001:1.0:5 | 0.3718 | 0.8744 |
| EN-001:1.0:12 | 0.5157 | 0.7847 |
| EN-001:1.0:3 | 0.4600 | 0.2367 |
| EN-001:1.0:2 | 0.4586 | 0.2188 |
| EN-001:1.0:7 | 0.4982 | 0.0231 |
| EN-001:1.0:4 | 0.4941 | 0.0162 |
| EN-001:1.0:6 | 0.4920 | 0.0128 |
| EN-001:1.0:10 | 0.4556 | 0.0074 |

- kept: ['EN-001:1.0:9']
- discarded: ['EN-001:1.0:1', 'EN-001:1.0:5', 'EN-001:1.0:12', 'EN-001:1.0:3', 'EN-001:1.0:2', 'EN-001:1.0:7', 'EN-001:1.0:4', 'EN-001:1.0:6', 'EN-001:1.0:10']
- covered_aspects: ['General categories of statutory family-related leave that might apply (maternity, paternity, adoption, shared parental, etc.)', 'Notification process to manager and HR']
- missing_aspects: ['Specific statutory duration/length of entitlement for maternity or paternity leave', 'How eligibility and personal circumstances determine the exact duration', 'Pay arrangements during the leave']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: "Fragment 0 identifies the applicable leave categories and notes HR determines eligibility and duration, but it does not state the actual length of entitlement, leaving the key 'how long' aspect unanswered."

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-17 — england-employee (expected: abstain)

**Question:** Does Northfern Technologies provide any life insurance benefit for employees in England?

**Expected answer summary:** —
**Expected aspects:** —

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** Not enough evidence was found to answer with confidence.

**Citations:** none

**Attempt 1** — query: 'Does Northfern Technologies provide any life insurance benefit for employees in England?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:0 | 0.3972 | 0.9122 |
| EN-001:1.0:7 | 0.3631 | 0.8398 |
| GLB-001:1.0:1 | 0.4401 | 0.8319 |
| GLB-002:1.0:1 | 0.4126 | 0.7900 |
| GLB-001:1.0:12 | 0.4336 | 0.6257 |
| GLB-001:1.0:0 | 0.4852 | 0.4698 |
| GLB-002:1.0:0 | 0.4713 | 0.2394 |
| GLB-001:1.0:8 | 0.4472 | 0.1565 |
| GLB-001:1.0:5 | 0.4193 | 0.0988 |
| GLB-002:1.0:4 | 0.4463 | 0.0258 |

- kept: []
- discarded: ['EN-001:1.0:0', 'EN-001:1.0:7', 'GLB-001:1.0:1', 'GLB-002:1.0:1', 'GLB-001:1.0:12', 'GLB-001:1.0:0', 'GLB-002:1.0:0', 'GLB-001:1.0:8', 'GLB-001:1.0:5', 'GLB-002:1.0:4']
- covered_aspects: []
- missing_aspects: ['whether Northfern Technologies offers life insurance benefit to England employees', 'details of any life insurance coverage, eligibility, or terms']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments mention life insurance or any related benefit; they cover annual leave, personal days, code of conduct, and information security, none of which address life insurance.'

**Attempt 2** — query: 'Northfern Technologies employee life insurance coverage eligibility terms England benefits policy'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:1 | 0.4242 | 0.9931 |
| EN-001:1.0:0 | 0.3411 | 0.9636 |
| EN-001:1.0:7 | 0.3612 | 0.4379 |
| GLB-001:1.0:0 | 0.4321 | 0.3402 |
| GLB-002:1.0:1 | 0.3789 | 0.2188 |
| GLB-001:1.0:12 | 0.4031 | 0.1940 |
| GLB-001:1.0:1 | 0.4113 | 0.1252 |
| GLB-002:1.0:0 | 0.4173 | 0.0471 |
| GLB-001:1.0:5 | 0.3679 | 0.0340 |
| GLB-002:1.0:4 | 0.4325 | 0.0300 |

- kept: []
- discarded: ['EN-001:1.0:1', 'EN-001:1.0:0', 'EN-001:1.0:7', 'GLB-001:1.0:0', 'GLB-002:1.0:1', 'GLB-001:1.0:12', 'GLB-001:1.0:1', 'GLB-002:1.0:0', 'GLB-001:1.0:5', 'GLB-002:1.0:4']
- covered_aspects: []
- missing_aspects: ['life insurance benefit details for England employees']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'None of the retrieved fragments mention life insurance or any related benefit; they cover annual leave, personal days, code of conduct, and information security, which are unrelated to the question.'

**Attempt 3** — query: 'Northfern Technologies UK employee benefits life assurance policy England'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| EN-001:1.0:7 | 0.3440 | 0.9806 |
| EN-001:1.0:0 | 0.3419 | 0.9760 |
| EN-001:1.0:1 | 0.3853 | 0.9676 |
| GLB-001:1.0:12 | 0.4138 | 0.1595 |
| GLB-001:1.0:8 | 0.4329 | 0.0988 |
| GLB-002:1.0:1 | 0.3634 | 0.0619 |
| GLB-001:1.0:1 | 0.4221 | 0.0426 |
| GLB-001:1.0:5 | 0.3888 | 0.0252 |
| GLB-002:1.0:0 | 0.4291 | 0.0111 |
| GLB-002:1.0:4 | 0.4362 | 0.0044 |

- kept: []
- discarded: ['EN-001:1.0:7', 'EN-001:1.0:0', 'EN-001:1.0:1', 'GLB-001:1.0:12', 'GLB-001:1.0:8', 'GLB-002:1.0:1', 'GLB-001:1.0:1', 'GLB-001:1.0:5', 'GLB-002:1.0:0', 'GLB-002:1.0:4']
- covered_aspects: []
- missing_aspects: ['Whether Northfern Technologies offers life insurance benefit in England', 'Details of any life insurance policy or plan']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'The retrieved fragments cover annual leave, personal days, code of conduct, and information security policies, none of which mention life insurance benefits.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-18 — mexico-employee (expected: abstain)

**Question:** ¿Northfern ofrece algún programa de préstamos personales sin intereses para empleados de México en dificultades económicas?

**Expected answer summary:** —
**Expected aspects:** —

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: '¿Northfern ofrece algún programa de préstamos personales sin intereses para empleados de México en dificultades económicas?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:11 | 0.3701 | 0.9959 |
| MX-002:1.0:0 | 0.4006 | 0.9226 |
| MX-001:1.1:0 | 0.4051 | 0.8299 |
| GLB-001:1.0:1 | 0.5030 | 0.5693 |
| MX-001:1.1:1 | 0.4259 | 0.5278 |
| GLB-002:1.0:1 | 0.5005 | 0.0429 |
| MX-002:1.0:1 | 0.4206 | 0.0421 |
| GLB-001:1.0:5 | 0.5070 | 0.0328 |
| GLB-001:1.0:8 | 0.4737 | 0.0300 |
| GLB-002:1.0:4 | 0.4924 | 0.0093 |

- kept: []
- discarded: ['MX-001:1.1:11', 'MX-002:1.0:0', 'MX-001:1.1:0', 'GLB-001:1.0:1', 'MX-001:1.1:1', 'GLB-002:1.0:1', 'MX-002:1.0:1', 'GLB-001:1.0:5', 'GLB-001:1.0:8', 'GLB-002:1.0:4']
- covered_aspects: []
- missing_aspects: ['existencia de programa de préstamos personales sin intereses', 'condiciones de elegibilidad para dificultades económicas', 'proceso de solicitud de ayuda financiera']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos menciona préstamos personales, ayuda financiera o programas de asistencia económica para empleados; tratan de vacaciones, teletrabajo, código de conducta y seguridad de la información.'

**Attempt 2** — query: 'Política de asistencia financiera o préstamos de emergencia para empleados de México: requisitos y proceso de solicitud'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-001:1.1:15 | 0.4398 | 0.9726 |
| MX-001:1.1:13 | 0.4114 | 0.9664 |
| MX-001:1.1:11 | 0.4309 | 0.9532 |
| MX-001:1.1:2 | 0.3888 | 0.9472 |
| MX-002:1.0:2 | 0.4071 | 0.7507 |
| MX-002:1.0:12 | 0.4312 | 0.6384 |
| MX-002:1.0:0 | 0.4513 | 0.2393 |
| MX-001:1.1:1 | 0.4310 | 0.1793 |
| MX-001:1.1:0 | 0.4379 | 0.0802 |
| MX-002:1.0:8 | 0.4325 | 0.0688 |

- kept: []
- discarded: ['MX-001:1.1:15', 'MX-001:1.1:13', 'MX-001:1.1:11', 'MX-001:1.1:2', 'MX-002:1.0:2', 'MX-002:1.0:12', 'MX-002:1.0:0', 'MX-001:1.1:1', 'MX-001:1.1:0', 'MX-002:1.0:8']
- covered_aspects: []
- missing_aspects: ['Existencia de un programa de préstamos personales sin intereses para empleados de México', 'Condiciones de elegibilidad y proceso de solicitud para asistencia financiera']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos trata sobre préstamos personales o asistencia financiera para empleados; tratan de vacaciones, permisos, teletrabajo y ámbito de aplicación, por lo que no aportan evidencia relevante.'

**Attempt 3** — query: 'Programa de préstamos sin intereses para empleados de México: elegibilidad y solicitud'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| MX-002:1.0:4 | 0.4819 | 0.9850 |
| MX-001:1.1:2 | 0.4531 | 0.9237 |
| MX-001:1.1:11 | 0.4519 | 0.9170 |
| MX-002:1.0:2 | 0.4700 | 0.7600 |
| MX-002:1.0:12 | 0.4907 | 0.5696 |
| MX-002:1.0:0 | 0.4895 | 0.4571 |
| MX-001:1.1:5 | 0.5092 | 0.1874 |
| MX-001:1.1:14 | 0.5041 | 0.1349 |
| MX-002:1.0:3 | 0.4994 | 0.0732 |
| MX-002:1.0:8 | 0.4972 | 0.0084 |

- kept: []
- discarded: ['MX-002:1.0:4', 'MX-001:1.1:2', 'MX-001:1.1:11', 'MX-002:1.0:2', 'MX-002:1.0:12', 'MX-002:1.0:0', 'MX-001:1.1:5', 'MX-001:1.1:14', 'MX-002:1.0:3', 'MX-002:1.0:8']
- covered_aspects: []
- missing_aspects: ['existencia de un programa de préstamos personales sin intereses', 'condiciones de elegibilidad para asistencia financiera a empleados de México']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Ninguno de los fragmentos recuperados trata sobre préstamos personales o asistencia financiera; tratan de teletrabajo, vacaciones, días de asuntos personales y protección de datos, sin relación con la pregunta.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-19 — spain-employee (expected: abstain)

**Question:** Si tengo una ausencia que no encaja claramente en ninguna categoría administrativa habitual en España, ¿qué procedimiento sigue RR. HH. para decidir cómo se tramita, y cuándo consulta al área Legal?

**Expected answer summary:** —
**Expected aspects:** ['Existe un procedimiento real descrito en ES-007 §5 (RR. HH. verifica la naturaleza de la solicitud y determina el circuito de tramitación; consulta a Legal si procede), pero no es accesible para este perfil']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Si tengo una ausencia que no encaja claramente en ninguna categoría administrativa habitual en España, ¿qué procedimiento sigue RR. HH. para decidir cómo se tramita, y cuándo consulta al área Legal?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-002:1.0:11 | 0.3126 | 0.9981 |
| ES-001:1.0:10 | 0.4067 | 0.9866 |
| ES-002:1.0:9 | 0.3984 | 0.9789 |
| ES-002:1.0:6 | 0.4042 | 0.9130 |
| ES-002:1.0:7 | 0.4100 | 0.8992 |
| ES-002:1.0:5 | 0.3928 | 0.8950 |
| ES-001:1.0:8 | 0.4410 | 0.7725 |
| ES-001:1.0:5 | 0.4215 | 0.6964 |
| ES-002:1.0:10 | 0.4437 | 0.6603 |
| ES-002:1.0:3 | 0.4492 | 0.2209 |

- kept: []
- discarded: ['ES-002:1.0:11', 'ES-001:1.0:10', 'ES-002:1.0:9', 'ES-002:1.0:6', 'ES-002:1.0:7', 'ES-002:1.0:5', 'ES-001:1.0:8', 'ES-001:1.0:5', 'ES-002:1.0:10', 'ES-002:1.0:3']
- covered_aspects: ['Indicación de que dudas sobre clasificación de ausencias se dirigen a RR. HH. de España']
- missing_aspects: ['Procedimiento interno que sigue RR. HH. para decidir la clasificación de una ausencia atípica', 'Criterios o pasos concretos de evaluación', 'Cuándo y por qué RR. HH. consulta al área Legal']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Los fragmentos solo indican que las dudas de clasificación se remiten a RR. HH. de España y que los procedimientos internos son de acceso restringido, pero no describen el procedimiento interno de decisión ni mencionan en ningún momento la intervención del área Legal, por lo que no ayudan a responder la pregunta.'

**Attempt 2** — query: 'Procedimiento de RR. HH. para clasificar ausencias atípicas no contempladas en las categorías estándar y criterios para escalar la consulta al departamento Legal'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-002:1.0:9 | 0.4354 | 0.9891 |
| ES-002:1.0:11 | 0.4162 | 0.9859 |
| ES-001:1.0:10 | 0.4545 | 0.9535 |
| ES-001:1.0:8 | 0.4739 | 0.5187 |
| ES-002:1.0:5 | 0.4398 | 0.3110 |
| GLB-001:1.0:11 | 0.4505 | 0.2992 |
| ES-002:1.0:6 | 0.4543 | 0.2659 |
| ES-002:1.0:10 | 0.4592 | 0.1113 |
| ES-002:1.0:7 | 0.4782 | 0.1019 |
| ES-004:1.0:12 | 0.4665 | 0.0049 |

- kept: ['ES-002:1.0:11', 'ES-002:1.0:5', 'ES-002:1.0:6', 'ES-002:1.0:7', 'ES-002:1.0:9']
- discarded: ['ES-001:1.0:10', 'ES-001:1.0:8', 'GLB-001:1.0:11', 'ES-002:1.0:10', 'ES-004:1.0:12']
- covered_aspects: ['General process of reporting unusual absences and HR classifying them (ES-002 secciones 6-9)', 'HR resolves classification questions and exceptions (ES-002 sección 11)', 'References to restricted internal HR procedures documents (ES-006, ES-007)']
- missing_aspects: ["Specific internal procedure HR follows to decide classification of an absence that doesn't fit standard categories", 'Criteria or process for when/how HR escalates or consults the Legal department', 'Access to the restricted ES-007 procedures document content']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Fragments describe general reporting and classification responsibilities of HR but explicitly state that internal decision procedures (e.g., ES-007) are restricted and not covered here; nothing addresses consultation with Legal, so the question remains only partially answered.'

**Attempt 3** — query: 'Documento interno ES-007 procedimiento RR. HH. casos excepcionales ausencias: pasos de decisión y criterios de consulta o escalado a Legal'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:8 | 0.4242 | 0.9994 |
| ES-002:1.0:11 | 0.3119 | 0.9910 |
| ES-001:1.0:10 | 0.3594 | 0.9835 |
| GLB-002:1.0:11 | 0.4290 | 0.9773 |
| ES-002:1.0:7 | 0.4538 | 0.7175 |
| ES-002:1.0:5 | 0.4480 | 0.7056 |
| ES-002:1.0:6 | 0.4335 | 0.6866 |
| GLB-001:1.0:11 | 0.4260 | 0.6623 |
| ES-002:1.0:10 | 0.4164 | 0.4267 |
| ES-002:1.0:8 | 0.4433 | 0.2944 |

- kept: ['ES-001:1.0:10', 'ES-002:1.0:11']
- discarded: ['ES-002:1.0:9', 'ES-002:1.0:5', 'ES-002:1.0:6', 'ES-002:1.0:7', 'ES-001:1.0:8', 'GLB-002:1.0:11', 'GLB-001:1.0:11', 'ES-002:1.0:10', 'ES-002:1.0:8']
- covered_aspects: ['Dónde dirigirse para dudas de clasificación de una ausencia (Recursos Humanos de España)', 'Indicación de que excepciones/clasificaciones especiales requieren intervención de RR.HH.', 'Referencia a que procedimientos internos detallados están en documentos de acceso restringido (ES-006, ES-007)']
- missing_aspects: ['Procedimiento interno específico que sigue RR.HH. para decidir la clasificación de una ausencia atípica', 'Criterios o pasos concretos de evaluación interna', 'Cuándo y bajo qué circunstancias RR.HH. consulta al área Legal']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos indican que las dudas de clasificación se dirigen a RR.HH. y que el procedimiento detallado está en documentos restringidos (ES-007), pero no describen el procedimiento interno real ni mencionan en ningún momento la intervención del área Legal, por lo que falta información clave.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-20 — spain-manager (expected: abstain)

**Question:** Como manager en España, si un colaborador de México me pregunta si debe usar sus vacaciones pendientes antes de una fecha límite como el 31 de marzo, igual que en España, ¿qué le respondo sobre la regla aplicable en México?

**Expected answer summary:** —
**Expected aspects:** ['Existe una regla real en MX-001 §7 sobre vacaciones pendientes en México, pero no es accesible para este perfil']

**Abstained:** True  ·  **Retrievals:** 3

**Answer:** No se encontró evidencia suficiente para responder con garantías.

**Citations:** none

**Attempt 1** — query: 'Como manager en España, si un colaborador de México me pregunta si debe usar sus vacaciones pendientes antes de una fecha límite como el 31 de marzo, igual que en España, ¿qué le respondo sobre la regla aplicable en México?'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:7 | 0.3534 | 0.9982 |
| ES-006:1.0:2 | 0.4120 | 0.9961 |
| ES-006:1.0:4 | 0.3391 | 0.9929 |
| ES-004:1.0:2 | 0.4049 | 0.9757 |
| ES-001:1.0:9 | 0.3882 | 0.9712 |
| ES-001:1.0:8 | 0.3749 | 0.9496 |
| ES-006:1.0:8 | 0.3783 | 0.9357 |
| ES-001:1.0:6 | 0.4119 | 0.4735 |
| ES-001:1.0:4 | 0.3710 | 0.2010 |
| GLB-002:1.0:7 | 0.4065 | 0.1391 |

- kept: ['ES-001:1.0:7', 'ES-004:1.0:2']
- discarded: ['ES-006:1.0:2', 'ES-006:1.0:4', 'ES-001:1.0:9', 'ES-001:1.0:8', 'ES-006:1.0:8', 'ES-001:1.0:6', 'ES-001:1.0:4', 'GLB-002:1.0:7']
- covered_aspects: ['Regla española del 31 de marzo para vacaciones pendientes', 'Indicación de que las políticas de México son distintas y no intercambiables con las de España', 'Alcance del manager limitado a subordinados directos en España']
- missing_aspects: ['Contenido específico de la política de vacaciones de México (plazo límite para usar días pendientes)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos confirman la regla española y advierten que México tiene condiciones distintas, pero ningún fragmento contiene la regla mexicana aplicable, que es lo que realmente se necesita para responder.'

**Attempt 2** — query: 'Política de vacaciones México: plazo límite para usar días pendientes de vacaciones'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:7 | 0.2789 | 0.9994 |
| ES-001:1.0:5 | 0.4662 | 0.9738 |
| ES-002:1.0:1 | 0.4537 | 0.9601 |
| ES-006:1.0:4 | 0.3958 | 0.9398 |
| ES-001:1.0:4 | 0.3562 | 0.9250 |
| ES-001:1.0:6 | 0.3564 | 0.9236 |
| ES-001:1.0:3 | 0.4213 | 0.8827 |
| ES-001:1.0:8 | 0.4116 | 0.3756 |
| ES-001:1.0:9 | 0.4733 | 0.1478 |
| ES-002:1.0:4 | 0.4710 | 0.1411 |

- kept: ['ES-001:1.0:7', 'ES-004:1.0:2']
- discarded: ['ES-001:1.0:5', 'ES-002:1.0:1', 'ES-006:1.0:4', 'ES-001:1.0:4', 'ES-001:1.0:6', 'ES-001:1.0:3', 'ES-001:1.0:8', 'ES-001:1.0:9', 'ES-002:1.0:4']
- covered_aspects: ['Regla española del 31 de marzo para vacaciones pendientes', 'Indicación de que las políticas de México y España no son intercambiables']
- missing_aspects: ['Regla específica de México sobre fecha límite para usar vacaciones pendientes (contenido de la política mexicana)']
- grader route: ambiguous  ·  effective route: ambiguous  ·  rationale: 'Los fragmentos explican la regla española y aclaran que la política mexicana es distinta y no intercambiable, pero no contienen el texto de la política de México con su propia regla de fecha límite, que es lo que realmente se pregunta.'

**Attempt 3** — query: 'Vencimiento o caducidad de días de vacaciones no utilizados para empleados en México según política de la empresa'

| chunk_id | distance | rerank_score |
|---|---:|---:|
| ES-001:1.0:7 | 0.4037 | 0.9881 |
| ES-001:1.0:3 | 0.3833 | 0.9467 |
| ES-001:1.0:1 | 0.4110 | 0.7712 |
| ES-002:1.0:1 | 0.3918 | 0.4793 |
| ES-001:1.0:0 | 0.4148 | 0.4070 |
| ES-003:1.0:12 | 0.4405 | 0.2722 |
| ES-006:1.0:4 | 0.4271 | 0.2245 |
| ES-002:1.0:4 | 0.4440 | 0.1884 |
| ES-001:1.0:8 | 0.4390 | 0.1692 |
| ES-001:1.0:2 | 0.4124 | 0.0079 |

- kept: []
- discarded: ['ES-001:1.0:7', 'ES-004:1.0:2', 'ES-001:1.0:3', 'ES-001:1.0:1', 'ES-002:1.0:1', 'ES-001:1.0:0', 'ES-003:1.0:12', 'ES-006:1.0:4', 'ES-002:1.0:4', 'ES-001:1.0:8', 'ES-001:1.0:2']
- covered_aspects: ['Regla española del 31 de marzo para vacaciones pendientes', 'Confirmación de que las políticas de México no son intercambiables con las de España']
- missing_aspects: ['Contenido específico de la política de vacaciones de México (plazo límite para usar días pendientes)']
- grader route: insufficient  ·  effective route: insufficient  ·  rationale: 'Los fragmentos solo confirman la regla española y que México tiene una política distinta, pero ninguno expone el contenido real de la política mexicana sobre fecha límite de vacaciones pendientes.'

**Outcome check:** matches_expected=True
**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---
