# RAG Baseline Evaluation Report

## Configuración de la evaluación

- Generated: 2026-11-17T19:57:53.808238+00:00
- Variant: rag
- Dataset: docs\evaluation\eval-questions.yaml (20 preguntas: 14 answerable + 6 abstain)
- Embedding model: BAAI/bge-m3, revision `5617a9f61b028005a4858fdac845db406aefb181`, 1024 dims
- Generation model: claude-sonnet-5 (thinking disabled)
- top_k: 5
- Preguntas completadas: 20/20
- Revisión manual: 20/20 completada (ver "Resumen de la revisión manual" abajo)

## Automatic metrics

- Evidence recall@k (micro-averaged, answerable only): 1.0
- Answerable questions with ALL expected evidence retrieved: 1.0
- Answerable questions with ANY expected evidence retrieved: 1.0
- Answerable questions actually answered (not abstained): 1.0
- Abstain questions correctly abstained: 0.8333333333333334
- Citations structurally valid (reference a retrieved chunk): 1.0

These automatic metrics describe retrieval coverage, abstention behavior, and citation structure. They do not determine whether an answer is factually correct or whether its evidence is actually sufficient — see the manual review fields below and in the JSON results file for that.

## Resumen de la revisión manual

Se revisaron las 20 preguntas contrastando cada respuesta generada con el texto real de sus fragmentos citados (y, en los casos de abstención, con el texto de los fragmentos efectivamente recuperados aunque no citados) y con el resultado/resumen esperado del dataset.

- **factual_correctness:** 19/20 `correct`, 1/20 `incorrect` (`eval-17`, ver análisis abajo).
- **evidence_sufficiency:** `sufficient` en las 14 preguntas respondibles (sus fragmentos citados sustentan la respuesta por sí solos). `insufficient` en `eval-17`: aunque es una pregunta de abstención en el dataset, el sistema respondió como si fuera respondible, así que se evalúa con el mismo criterio — y el fragmento citado no sustenta la conclusión personal que el modelo extrajo de él. En las 5 abstenciones correctas restantes (`eval-15`, `16`, `18`, `19`, `20`) este campo se marca `not_applicable`, ya que no existe un objetivo de evidencia que medir (ver `docs/evaluation/eval-questions.yaml`, `expected_evidence: []`).
- **citation_support:** `supported` en las 14 preguntas respondibles correctas; `unsupported` en `eval-17`; `not_applicable` en las 5 abstenciones correctas restantes (una abstención nunca lleva citas formales — ver `generation.py`, `_to_generated_answer` — por lo que no hay nada que verificar estructuralmente, aunque sí se revisó manualmente que el texto de la abstención no inventara nada; ver más abajo el caso `eval-16`).
- **Ninguna respuesta respondible se marcó `incorrect`.** Las 14 respuestas respondibles reproducen fielmente el contenido de sus fragmentos citados, sin afirmaciones no respaldadas ni combinaciones indebidas de fragmentos distintos.
- **Un solo fallo real: `eval-17`** (detalle abajo) — es también la única discrepancia que ya señalaban las métricas automáticas (`abstain_correct_rate = 5/6`).
- **Ninguna filtración de contenido restringido detectada.** La mención de "ES-006 y ES-007" en la respuesta de `eval-16` se verificó contra el corpus fuente y corresponde a un fragmento accesible (`ES-002:1.0:11`) que solo nombra esos documentos como restringidos, sin revelar su contenido — ver comparación `eval-09`/`eval-16` abajo.

## Análisis: eval-17 — teletrabajo desde otro país

**Pregunta:** «¿Tengo autorizada la modalidad de teletrabajo desde otro país?» (perfil `mexico-employee`, resultado esperado: `abstain` / `personal_data_unavailable`).

El sistema respondió "No" en lugar de abstenerse (`outcome_check.matches_expected = false`; único caso entre las 20 preguntas). El único fragmento citado, `MX-002:1.0:8`, dice literalmente:

> "Trabajar temporalmente desde fuera de México **requiere autorización específica previa**, incluso si el empleado utiliza un dispositivo corporativo y una conexión segura. [...] Una autorización para viajar o asistir a un evento no implica autorización para teletrabajar desde el país de destino."

Este fragmento establece una **regla general de procedimiento** (se necesita autorización previa) pero **no contiene ningún dato sobre el estado de autorización personal de este empleado concreto** — ninguna política de este corpus podría contenerlo, por la misma razón que `eval-15` (saldo de vacaciones) no puede responderse desde la política. El modelo trató la ausencia de autorización explícita en el texto como si equivaliera a "no tienes autorización", cuando en realidad la pregunta es sobre un hecho individual que el corpus nunca podría confirmar ni descartar.

**Clasificación:** `factual_correctness=incorrect`, `evidence_sufficiency=insufficient`, `citation_support=unsupported`. Es un fallo de razonamiento del generador (confunde una regla con un hecho individual), no un fallo de retrieval: el fragmento recuperado es el correcto y más relevante disponible; el problema es la conclusión que el modelo extrae de él. Debería haberse abstenido con `abstain_reason=personal_data_unavailable`, igual que en `eval-15`.

## eval-09 / eval-16 — control de acceso (RLS)

`eval-09` (perfil `spain-hr`) y `eval-16` (perfil `spain-employee`) comparten **el mismo texto de pregunta exacto**, sobre el contenido del expediente interno de excepciones de vacaciones (ES-007 §4, documento `allowed_roles=[hr]`).

- **`eval-09` (spain-hr):** recupera `ES-007:1.0:4` en el puesto 0 y responde con los cuatro elementos exactos del expediente, citando esa fuente. Correcto.
- **`eval-16` (spain-employee):** su lista completa de fragmentos recuperados es `ES-001:1.0:8`, `ES-002:1.0:11`, `ES-001:1.0:6`, `ES-002:1.0:4`, `ES-002:1.0:7` — **ningún fragmento de ES-006 ni ES-007 aparece**, confirmando que RLS filtró correctamente esos documentos antes de que llegaran al generador. El sistema se abstiene, correctamente.

**Punto señalado para revisión:** la respuesta de `eval-16` nombra "ES-006 y ES-007" explícitamente, aunque no cita ningún fragmento (una abstención nunca lleva citas formales). Se verificó contra el corpus fuente (`data/corpus/spain/ES-002-permisos-y-ausencias.md`, §11 "Consultas, excepciones y documentos relacionados", chunk `ES-002:1.0:11`) que ese texto — uno de los cinco fragmentos efectivamente recuperados y accesibles para `spain-employee` — nombra literalmente "ES-006" y "ES-007" y los describe como de acceso restringido, sin reproducir su contenido:

> "- **ES-006 — Gestión de ausencias:** guía de uso restringido para managers de España [...]
> - **ES-007 — Procedimientos internos de RR. HH.:** procedimientos de acceso restringido al equipo de Recursos Humanos de España."

**Conclusión verificada (no una observación pendiente): no hay filtración.** El modelo se apoyó en un fragmento accesible y no citado para nombrar los documentos restringidos — lo cual es información pública en sí misma (qué documentos existen y que están restringidos) — pero nunca tuvo acceso a, ni reveló, el contenido real de ES-006/ES-007. El comportamiento de RLS es correcto en ambos perfiles para la misma consulta.

## Limitaciones del baseline

- **Las abstenciones nunca llevan citas formales**, incluso cuando están bien fundamentadas en un fragmento concreto (ver `eval-15`, `eval-16`, `eval-18`–`eval-20`). Esto es coherente con `generation.py` (`_to_generated_answer`: `citations` siempre `[]` cuando `abstained=True`), pero significa que `citation_support`/`evidence_sufficiency` no se pueden verificar automáticamente en ninguna abstención — solo mediante revisión manual del texto generado y de los fragmentos recuperados, como se ha hecho aquí.
- **El único fallo real (`eval-17`) es de razonamiento, no de retrieval ni de citación estructural**: el fragmento correcto fue recuperado y citado, pero el modelo extrajo de él una conclusión personal que el fragmento no sustenta. Ningún umbral de distancia (Fase 10.3) ni ninguna comprobación estructural de citas habría detectado este fallo — exige revisión semántica humana o, más adelante, un mecanismo de verificación de la respuesta en sí (p. ej. CRAG), no cambios en retrieval.
- **n=6 en preguntas de abstención (una por `abstain_reason` salvo `personal_data_unavailable`, con dos)** es una muestra pequeña: una tasa de acierto de 5/6 no debe generalizarse como "83 % de fiabilidad en abstención" sin más datos. Mismo criterio de cautela ya aplicado en la Fase 10.3 para el umbral de distancia.
- **La revisión de corrección factual y suficiencia de evidencia es manual**, por diseño (ver Fase 10.4, sin LLM-as-judge ni frameworks externos). Esto es deliberado y reproducible, pero no escala más allá de un conjunto de preguntas pequeño como este.
- **Verificar que una mención como "ES-006 y ES-007" en `eval-16` no fuera una filtración exigió leer el corpus fuente directamente** (no solo el JSON de resultados, que no almacena el texto de fragmentos no citados). Para un conjunto de evaluación mayor, esta verificación manual de "no-filtración" dejaría de ser practicable sin herramienta adicional.

## Per-question review

### eval-01 — spain-employee (expected: answerable)

**Question:** ¿Cuántos días laborables de vacaciones tiene un empleado en España por año completo de servicio?

**Expected answer summary:** 23 días laborables por año completo de servicio.

**Actual answer (abstained=False):** Con carácter general, cada empleado en España dispone de 23 días laborables de vacaciones por año completo de servicio.

**Citations:**
- ES-001 v1.0 — 3. Vacaciones anuales (`ES-001:1.0:3`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Respuesta coincide literalmente con ES-001 §3 (23 días laborables); sin información inventada.

---

### eval-02 — mexico-employee (expected: answerable)

**Question:** Según el Código de Conducta, ¿a partir de qué valor de un regalo se requiere revisión previa de un representante autorizado de la empresa antes de aceptarlo u ofrecerlo?

**Expected answer summary:** A partir de EUR 50 (o el equivalente en moneda local); por debajo de ese umbral no se permite automáticamente, y los regalos en efectivo o equivalentes están prohibidos en todo caso.

**Actual answer (abstained=False):** Según el Código de Conducta (GLB-001, sección 4), el umbral indicativo para un regalo es de 50 EUR (o el equivalente en moneda local). Los regalos que superen ese umbral requieren revisión por parte de un representante autorizado de la empresa antes de ser aceptados u ofrecidos. Cabe destacar que un regalo igual o inferior a ese umbral no está automáticamente permitido: los regalos en efectivo o equivalentes, los incentivos indebidos y los regalos que generen un conflicto de interés real o percibido están prohibidos independientemente de su valor.

**Citations:**
- GLB-001 v1.0 — 4. Gifts, hospitality, and business courtesies (`GLB-001:1.0:4`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Umbral de 50 EUR y prohibición de efectivo/conflictos de interés reproducidos fielmente desde GLB-001 §4.

---

### eval-03 — spain-employee (expected: answerable)

**Question:** ¿Cuál es el máximo ordinario de días laborables consecutivos de vacaciones que se pueden solicitar en España?

**Expected answer summary:** Hasta 15 días laborables consecutivos, como regla ordinaria.

**Actual answer (abstained=False):** Como regla ordinaria, en España se pueden solicitar hasta 15 días laborables consecutivos de vacaciones. Los periodos superiores a ese límite requieren una autorización excepcional según el procedimiento correspondiente.

**Citations:**
- ES-001 v1.0 — 6. Periodos consecutivos (`ES-001:1.0:6`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Límite de 15 días consecutivos y referencia a excepciones (§8) coinciden con ES-001 §6.

---

### eval-04 — spain-employee (expected: answerable)

**Question:** ¿Cuántos días de teletrabajo a la semana puede hacer un empleado elegible en España?

**Expected answer summary:** Hasta 3 días de teletrabajo por semana, manteniendo al menos 2 días de presencia.

**Actual answer (abstained=False):** Un empleado con un puesto elegible puede teletrabajar, como régimen ordinario, hasta tres días por semana, manteniendo al menos dos días de presencia en su centro de trabajo asignado. Se trata de un máximo ordinario y no de un derecho automático a elegir tres días todas las semanas; los días concretos se coordinan con el responsable directo y el calendario puede variar según necesidades justificadas de organización. Además, en circunstancias puntuales puede estudiarse la autorización de un cuarto día de teletrabajo u otra adaptación temporal, pero esto depende de las circunstancias y de las aprobaciones necesarias, y una excepción concedida para una semana no modifica automáticamente el régimen habitual.

**Citations:**
- ES-003 v1.0 — 3. Régimen ordinario de teletrabajo (`ES-003:1.0:3`)
- ES-003 v1.0 — 6. Teletrabajo adicional y excepciones (`ES-003:1.0:7`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Combina correctamente la regla ordinaria (ES-003 §3) con la excepción del cuarto día (ES-003 §7) sin presentar la excepción como automática.

---

### eval-05 — spain-employee (expected: answerable)

**Question:** ¿Cuál es el presupuesto anual de formación por empleado en España?

**Expected answer summary:** 1.200 € de referencia por año natural, no acumulable de un año a otro.

**Actual answer (abstained=False):** Según la política ES-004, cada empleado en España dispone de una asignación de referencia de 1.200 € por año natural para actividades de formación relacionadas con su puesto actual o su desarrollo profesional. Este presupuesto es individual, no se acumula de un año a otro, y disponer del mismo no equivale a una aprobación automática de cualquier gasto.

**Citations:**
- ES-004 v1.0 — 3. Presupuesto anual de formación (`ES-004:1.0:3`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 1.200 €/año, no acumulable, sin aprobación automática: coincide con ES-004 §3.

---

### eval-06 — spain-employee (expected: answerable)

**Question:** ¿A partir de qué antigüedad puede un empleado en España acceder al seguro médico privado voluntario?

**Expected answer summary:** A partir de los seis meses de antigüedad, cumpliendo las condiciones administrativas del programa.

**Actual answer (abstained=False):** Un empleado en España puede acceder voluntariamente al programa corporativo de seguro médico privado a partir de los seis meses de antigüedad, calculados desde la fecha de incorporación que conste en el registro corporativo, siempre que se cumplan las condiciones administrativas del programa y se tramite el alta correspondiente.

**Citations:**
- ES-004 v1.0 — 7. Seguro médico privado (`ES-004:1.0:8`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 6 meses de antigüedad y trámite de alta: coincide con ES-004 §7 (Seguro médico privado).

---

### eval-07 — spain-employee (expected: answerable)

**Question:** ¿Cuál es el límite máximo de reembolso por noche de alojamiento en un viaje de trabajo dentro de España?

**Expected answer summary:** 120 € por noche dentro de España (180 € fuera de España), como límite máximo del gasto real justificado.

**Actual answer (abstained=False):** El límite máximo de reembolso por noche de alojamiento en un viaje de trabajo dentro de España es de 120 € por noche. Este importe es un límite máximo, no una cantidad fija, por lo que se reembolsa el gasto real profesional justificado hasta ese máximo.

**Citations:**
- ES-005 v1.0 — 5. Alojamiento (`ES-005:1.0:5`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 120 €/noche dentro de España, límite máximo no importe fijo: coincide con ES-005 §5.

---

### eval-08 — spain-manager (expected: answerable)

**Question:** Como manager en España, ¿qué debo hacer si un empleado solicita más de 15 días laborables consecutivos de vacaciones?

**Expected answer summary:** El manager no puede concederlo por sí solo; debe remitir la solicitud a RR. HH. España para su valoración excepcional.

**Actual answer (abstained=False):** Si un empleado solicita más de 15 días laborables consecutivos de vacaciones, se supera el límite ordinario establecido (hasta 15 días laborables consecutivos como regla general). Esto requiere una autorización excepcional, por lo que usted, como manager, no puede aprobarla por sí solo: debe remitir la solicitud a Recursos Humanos de España para su valoración, ya que este tipo de casos está específicamente contemplado entre los que deben escalarse. La autorización de la excepción, si procede, debe quedar registrada en el sistema corporativo correspondiente.

**Citations:**
- ES-006 v1.0 — 4. Gestión de vacaciones (`ES-006:1.0:4`)
- ES-006 v1.0 — 8. Excepciones y escalado (`ES-006:1.0:8`)
- ES-001 v1.0 — 6. Periodos consecutivos (`ES-001:1.0:6`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Combina ES-006 §4 y §8 (escalado obligatorio a RR. HH., el manager no puede aprobar la excepción) y ES-001 §6 (límite de 15 días); sin afirmaciones no respaldadas.

---

### eval-09 — spain-hr (expected: answerable)

**Question:** ¿Qué debe recoger el expediente interno de RR. HH. al revisar una excepción de vacaciones de más de 15 días laborables consecutivos en España?

**Expected answer summary:** Periodo solicitado y saldo verificado, motivo de la excepcionalidad, valoración del responsable sobre cobertura, y propuesta de resolución con la autoridad que debe decidir.

**Actual answer (abstained=False):** Según el procedimiento interno de RR. HH. España (ES-007), al revisar una solicitud de vacaciones que supere el límite ordinario de 15 días laborables consecutivos, el expediente debe recoger: el periodo solicitado y el saldo disponible, verificado en el sistema de personal; el motivo de la excepcionalidad, descrito con el mínimo detalle necesario; la valoración del responsable sobre la cobertura del equipo y la continuidad operativa; y una propuesta de resolución junto con la autoridad que debe decidir. RR. HH. comprobará que se ha seguido el procedimiento y coordinará la autorización correspondiente, aunque la remisión a RR. HH. no implica aprobación automática, respetándose en todo caso los derechos legales y acuerdos individuales aplicables.

**Citations:**
- ES-007 v1.0 — 4. Excepciones de vacaciones (`ES-007:1.0:4`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Reproduce los cuatro elementos del expediente (periodo/saldo, motivo, valoración de cobertura, propuesta+autoridad) tal como figuran en ES-007 §4, bajo el perfil spain-hr que sí tiene acceso. Ver comparación con eval-16 arriba.

---

### eval-10 — mexico-employee (expected: answerable)

**Question:** Para un empleado con 3 años de antigüedad cumplida en México, ¿cuántos días laborables de vacaciones le corresponden según la escala interna?

**Expected answer summary:** 18 días laborables, según la fila de 3 años de la escala de antigüedad.

**Actual answer (abstained=False):** Según la escala interna de Northfern para México, un empleado con 3 años de antigüedad cumplida tiene derecho a 18 días laborables anuales de vacaciones.

**Citations:**
- MX-001 v1.1 — 3. Vacaciones anuales y antigüedad (`MX-001:1.1:4`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 18 días para 3 años de antigüedad: coincide exactamente con la fila de la tabla de MX-001 §3 (v1.1).

---

### eval-11 — mexico-employee (expected: answerable)

**Question:** ¿Existe en México un límite corporativo ordinario de días laborables consecutivos de vacaciones, como el de 15 días de España?

**Expected answer summary:** No; a diferencia de la política española (ES-001), MX-001 no establece ese límite corporativo ordinario.

**Actual answer (abstained=False):** No. Según la política MX-001, a diferencia de la política española ES-001, la política de México no establece un límite corporativo ordinario de 15 días laborables consecutivos de vacaciones. La coordinación con el responsable buscará asegurar la continuidad del servicio, pero respetando siempre los periodos mínimos de disfrute continuo y demás derechos que establezca la normativa aplicable.

**Citations:**
- MX-001 v1.1 — 6. Periodos continuos y coordinación (`MX-001:1.1:9`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: Confirma la ausencia de límite ordinario de 15 días consecutivos en México, tal como lo señala explícitamente MX-001 §6 en contraste con ES-001.

---

### eval-12 — mexico-employee (expected: answerable)

**Question:** ¿Cuántos días de teletrabajo a la semana puede hacer un empleado elegible en México?

**Expected answer summary:** Hasta 2 días de teletrabajo por semana, manteniendo al menos 3 días de presencia.

**Actual answer (abstained=False):** Los puestos elegibles en México pueden realizar hasta dos días de teletrabajo por semana, manteniendo al menos tres días de presencia en el centro de trabajo asignado, como régimen interno habitual. Sin embargo, la elegibilidad de un puesto no equivale a una autorización automática para cualquier distribución semanal, ya que los días de teletrabajo deben coordinarse previamente con el responsable directo.

**Citations:**
- MX-002 v1.0 — 3. Modalidad habitual de teletrabajo (`MX-002:1.0:3`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 2 días/semana, mínimo 3 de presencia: coincide con MX-002 §3.

---

### eval-13 — england-employee (expected: answerable)

**Question:** What is the annual leave entitlement for a full-time employee in England, and what else is it entitled to on top of it?

**Expected answer summary:** 25 working days of paid annual leave per complete holiday year, plus the applicable bank/public holidays (not deducted from the 25 days).

**Actual answer (abstained=False):** A full-time employee in England working a standard five-day week receives 25 working days of paid annual leave per complete holiday year (which runs from 1 January to 31 December). On top of this, they are also entitled to the bank/public holidays applicable to their England work location, which are separate from the 25-day entitlement and must not be deducted from it. Additionally, eligible full-time employees receive 2 paid personal days per full holiday year, which are a separate company benefit from both annual leave and bank/public holidays.

**Citations:**
- EN-001 v1.0 — 2. Holiday year and annual entitlement (`EN-001:1.0:2`)
- EN-001 v1.0 — 7. Company-paid personal days (`EN-001:1.0:7`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 25 días + bank holidays (EN-001 §2) y 2 personal days adicionales (EN-001 §7); responde también a la parte "on top of it" de la pregunta sin inventar nada.

---

### eval-14 — england-employee (expected: answerable)

**Question:** How many company-paid personal days per holiday year does Northfern provide to eligible employees in England?

**Expected answer summary:** 2 paid personal days per full holiday year, separate from annual leave and bank/public holidays.

**Actual answer (abstained=False):** Northfern Technologies provides 2 paid personal days per full holiday year to eligible full-time employees in England, in addition to annual leave. These are separate from annual leave and bank/public holidays.

**Citations:**
- EN-001 v1.0 — 7. Company-paid personal days (`EN-001:1.0:7`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=sufficient citation_support=supported
notes: 2 personal days, separados de vacaciones y festivos: coincide con EN-001 §7.

---

### eval-15 — spain-employee (expected: abstain)

**Question:** ¿Cuántos días de vacaciones me quedan a mí este año?

**Expected answer summary:** —

**Actual answer (abstained=True):** No puedo responder a esta pregunta con la información disponible. La política indica que no contiene saldos personales de vacaciones: cada persona debe consultar su saldo actualizado en su registro individual dentro del sistema de gestión de personal.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=not_applicable citation_support=not_applicable
notes: Abstención justificada: ES-001 §3/§6 indican explícitamente que el saldo personal no está en la política; la explicación generada es fiel al contenido recuperado aunque, al abstenerse, no lleva citas formales (comportamiento esperado de generation.py).

---

### eval-16 — spain-employee (expected: abstain)

**Question:** ¿Qué debe recoger el expediente interno de RR. HH. al revisar una excepción de vacaciones de más de 15 días laborables consecutivos en España?

**Expected answer summary:** —

**Actual answer (abstained=True):** Los fragmentos disponibles no especifican qué debe recoger exactamente el expediente interno de RR. HH. al revisar una excepción de vacaciones superior a 15 días laborables consecutivos. Solo indican que estas solicitudes requieren autorización excepcional conforme a la sección 8, que la persona empleada debe comunicar la circunstancia a su responsable directo, que este revisará el impacto sobre el equipo y, cuando corresponda, trasladará el caso a Recursos Humanos de España para su valoración, y que ninguna excepción se entiende aprobada por el mero hecho de solicitarla. Los criterios y pasos internos de evaluación se recogen en procedimientos de acceso restringido (como ES-006 y ES-007) que esta política no otorga acceso a consultar, por lo que no puedo precisar el contenido detallado del expediente.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=not_applicable citation_support=not_applicable
notes: Abstención correcta y RLS verificado (ver sección "eval-09 / eval-16" arriba): los 5 fragmentos recuperados para este perfil no incluyen ningún chunk de ES-006/ES-007. La mención de "ES-006 y ES-007" por nombre se verificó contra el corpus fuente (ES-002:1.0:11, fragmento accesible y efectivamente recuperado); no hay filtración de contenido restringido.

---

### eval-17 — mexico-employee (expected: abstain)

**Question:** ¿Tengo autorizada la modalidad de teletrabajo desde otro país?

**Expected answer summary:** —

**Actual answer (abstained=False):** No. Trabajar temporalmente desde fuera de México requiere una autorización específica previa, incluso si se usa un dispositivo corporativo y una conexión segura. La revisión puede involucrar a Recursos Humanos, Seguridad u otras áreas competentes, y una autorización para viajar o asistir a un evento no implica autorización para teletrabajar desde el país de destino. Por lo tanto, no se cuenta con autorización automática para teletrabajar desde otro país; debe solicitarse y obtenerse esa autorización específica antes de hacerlo.

**Citations:**
- MX-002 v1.0 — 8. Trabajo desde otro país (`MX-002:1.0:8`)

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=False

**Manual review:** factual_correctness=incorrect evidence_sufficiency=insufficient citation_support=unsupported
notes: FALLO DOCUMENTADO (ver análisis dedicado arriba): el fragmento citado solo establece la regla general de procedimiento, no el estado de autorización personal de este empleado; el modelo confunde ambas cosas. Único caso de abstención incorrecta de las 20 preguntas.

---

### eval-18 — spain-employee (expected: abstain)

**Question:** ¿La empresa paga una suscripción a Netflix como parte de los beneficios en España?

**Expected answer summary:** —

**Actual answer (abstained=True):** Los fragmentos disponibles no mencionan ninguna suscripción a Netflix ni beneficio similar entre los programas de formación, desarrollo profesional o beneficios complementarios descritos para España. No hay información suficiente para responder con confianza, por lo que prefiero abstenerme.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=not_applicable citation_support=not_applicable
notes: Abstención correcta por falta de evidencia; el texto generado confirma explícitamente que ningún fragmento recuperado (todos de ES-004/ES-002/ES-001) menciona Netflix ni beneficio equivalente.

---

### eval-19 — england-employee (expected: abstain)

**Question:** What is the vacation entitlement table based on seniority for employees in Mexico?

**Expected answer summary:** —

**Actual answer (abstained=True):** The retrieved context does not contain a vacation entitlement table based on seniority for employees in Mexico, nor any Mexico-specific leave policy. I cannot answer this question based on the available material.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=not_applicable citation_support=not_applicable
notes: Abstención correcta: RLS por país confirmado — ninguno de los 5 fragmentos recuperados para el perfil england-employee pertenece a MX-001 u otro documento de México.

---

### eval-20 — mexico-employee (expected: abstain)

**Question:** Does Northfern offer stock options or equity compensation to employees?

**Expected answer summary:** —

**Actual answer (abstained=True):** The retrieved policy fragments do not contain any information about stock options or equity compensation at Northfern Technologies. I cannot answer this question based on the available documents.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=correct evidence_sufficiency=not_applicable citation_support=not_applicable
notes: Abstención correcta: ningún fragmento recuperado (MX-001, GLB-001, MX-002) trata compensación en acciones; no_information verificado.

---
