# RAG Baseline Evaluation Report

- Generated: 2026-11-26T15:52:15.467955+00:00
- Variant: rag
- Dataset: docs\evaluation\crag-evaluation-questions.yaml
- top_k: 5

## Automatic metrics

- Evidence recall@k (micro-averaged, answerable only): 0.8571428571428571
- Answerable questions with ALL expected evidence retrieved: 0.8571428571428571
- Answerable questions with ANY expected evidence retrieved: 0.9285714285714286
- Answerable questions actually answered (not abstained): 0.9285714285714286
- Abstain questions correctly abstained: 1.0
- Citations structurally valid (reference a retrieved chunk): 1.0

These automatic metrics describe retrieval coverage, abstention behavior, and citation structure. They do not determine whether an answer is factually correct or whether its evidence is actually sufficient — see the manual review fields below and in the JSON results file for that.

## Per-question review

### eval-crag-01 — spain-employee (expected: answerable)

**Question:** ¿Con cuánta antelación debo solicitar mis vacaciones en España antes del primer día que quiero disfrutar?

**Expected answer summary:** Con al menos 15 días naturales de antelación respecto al primer día previsto de disfrute, salvo que se aplique una excepción justificada.

**Actual answer (abstained=False):** Con carácter ordinario, las vacaciones deben solicitarse con al menos 15 días naturales de antelación respecto al primer día previsto de disfrute. Este plazo puede exceptuarse únicamente ante circunstancias justificadas, siguiendo el procedimiento de excepciones: en ese caso, la persona empleada debe comunicarlo a su responsable directo, quien revisará el impacto y, si corresponde, trasladará el caso a Recursos Humanos de España para su valoración. En cualquier caso, ni una solicitud fuera de plazo ni una excepción se consideran aprobadas automáticamente; la decisión debe quedar confirmada por los canales internos establecidos.

**Citations:**
- ES-001 v1.0 — 4. Solicitud de vacaciones (`ES-001:1.0:4`)
- ES-001 v1.0 — 8. Excepciones (`ES-001:1.0:8`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-02 — spain-manager (expected: answerable)

**Question:** Como manager en España, si uno de mis colaboradores disfruta sus dos días anuales retribuidos por asuntos personales, ¿puedo descontarlos de su saldo de vacaciones?

**Expected answer summary:** No. Debo distinguir los dos días anuales retribuidos por asuntos personales de ES-002 de las vacaciones de ES-001, y no debo descontar automáticamente ese tipo de ausencia del saldo de vacaciones.

**Actual answer (abstained=False):** No. Según la política, los dos días anuales retribuidos por asuntos personales (regulados en ES-002) deben distinguirse de las vacaciones reguladas en ES-001. Como manager, no debe descontar automáticamente una ausencia del saldo de vacaciones; la clasificación y el registro deben corresponder al tipo de ausencia reconocido por la política y, cuando proceda, ser validado por RR. HH. Además, ES-002 establece expresamente que estos días no se descuentan del saldo de vacaciones regulado en ES-001.

**Citations:**
- ES-002 v1.0 — 4. Permiso interno por asuntos personales (`ES-002:1.0:4`)
- ES-006 v1.0 — 5. Ausencias planificadas (`ES-006:1.0:5`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-03 — spain-employee (expected: answerable)

**Question:** Si necesito ausentarme de mi puesto en España por una cita médica, ¿durante cuánto tiempo puedo comunicar la ausencia y debo avisar con antelación?

**Expected answer summary:** Puede comunicarse una ausencia por el tiempo indispensable que requiera la cita; siempre que sea posible, debe avisarse con antelación al responsable directo para coordinar el trabajo pendiente.

**Actual answer (abstained=False):** Puede comunicar la ausencia por el tiempo indispensable para acudir a la cita médica. Además, siempre que sea posible, debe avisar con antelación a su responsable directo para coordinar el trabajo pendiente. Tenga en cuenta que estas ausencias no se convierten automáticamente en vacaciones, y su clasificación administrativa y tratamiento retributivo dependerán de las condiciones aplicables al caso.

**Citations:**
- ES-002 v1.0 — 5. Citas médicas (`ES-002:1.0:5`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-04 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, ¿en qué plazo debe presentar un empleado los gastos de un viaje de trabajo después de finalizarlo?

**Expected answer summary:** Dentro de los 15 días naturales posteriores a la finalización del viaje, a través del canal corporativo autorizado, y con un justificante válido para cada gasto.

**Actual answer (abstained=False):** Los gastos de un viaje de trabajo deben presentarse a través del canal corporativo autorizado dentro de los 15 días naturales posteriores a la finalización del viaje.

**Citations:**
- ES-005 v1.0 — 8. Justificantes y presentación de gastos (`ES-005:1.0:8`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-05 — mexico-employee (expected: answerable)

**Question:** ¿Con cuántos días naturales de antelación debo presentar, como regla interna, una solicitud ordinaria de vacaciones en México?

**Expected answer summary:** Con al menos 10 días naturales de antelación, como regla de planificación interna, siempre que sea compatible con los derechos y plazos legales aplicables.

**Actual answer (abstained=False):** Como regla de planificación interna, las solicitudes ordinarias de vacaciones en México deben presentarse con al menos 10 días naturales de antelación, siempre que esto sea compatible con los derechos y plazos legales aplicables. Esta recomendación de antelación no elimina los derechos de disfrute del empleado ni habilita denegaciones contrarias a la legislación aplicable.

**Citations:**
- MX-001 v1.1 — 5. Solicitud ordinaria de vacaciones (`MX-001:1.1:8`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-06 — england-employee (expected: answerable)

**Question:** In England, what is the maximum number of consecutive working days of annual leave I can ordinarily request without needing special approval?

**Expected answer summary:** Up to 10 consecutive working days ordinarily; longer periods require advance discussion and special approval from the line manager in coordination with England HR.

**Actual answer (abstained=False):** In England, employees may ordinarily request up to 10 consecutive working days of annual leave without needing special approval. Longer periods require advance discussion and special approval from the line manager in coordination with England HR.

**Citations:**
- EN-001 v1.0 — 5. Consecutive leave and team coverage (`EN-001:1.0:5`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-07 — mexico-employee (expected: answerable)

**Question:** ¿Puedo usar brevemente el ordenador de la empresa para un asunto personal mientras trabajo en México?

**Expected answer summary:** Sí, el uso personal incidental puede permitirse cuando sea razonable, lícito y no interfiera con el trabajo ni infrinja otras normas de la empresa.

**Actual answer (abstained=False):** Sí. El uso incidental para fines personales de los dispositivos de la empresa puede estar permitido siempre que sea razonable, lícito y no interfiera con el trabajo ni infrinja otras normas de la empresa. En cualquier duda sobre el uso aceptable, se debe consultar al contacto correspondiente de IT o RRHH.

**Citations:**
- GLB-001 v1.0 — 6. Responsible use of company resources (`GLB-001:1.0:6`)

**Evidence recall:** 1/1 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-08 — spain-manager (expected: answerable)

**Question:** Como manager en España, uno de mis colaboradores solicita un periodo de vacaciones y tiene saldo suficiente. ¿Eso implica que debo aprobarlo automáticamente, y qué pasos concretos tengo que seguir antes de decidir?

**Expected answer summary:** No. Tener saldo suficiente no implica aprobación automática: debo valorar el calendario del equipo, los periodos de actividad crítica y la cobertura de funciones esenciales (ES-001 §5). En concreto, debo comprobar las fechas solicitadas y la cobertura operativa, identificar posibles coincidencias con otras ausencias ya aprobadas, revisar las condiciones aplicables de ES-001/ES-002, y registrar mi decisión y su justificación en el sistema corporativo (ES-006 §3).

**Actual answer (abstained=False):** No, tener saldo suficiente de vacaciones no implica la aprobación automática de las fechas solicitadas. La existencia de saldo suficiente no implica aprobación automática; hasta recibir confirmación, las vacaciones se consideran pendientes.

Antes de decidir, como manager debe seguir estos pasos:
1. Comprobar las fechas solicitadas y la cobertura operativa del equipo.
2. Identificar posibles coincidencias con otras ausencias ya aprobadas.
3. Revisar las condiciones aplicables en ES-001 o ES-002, según corresponda.
4. Registrar la decisión y su justificación operativa en el sistema corporativo.
5. Escalar a RR. HH. los casos que excedan su ámbito de decisión.

Además, debe tener en cuenta el calendario del equipo, los periodos de actividad crítica y la cobertura de funciones esenciales al evaluar la solicitud, así como valorar los compromisos del equipo, las sustituciones disponibles y los periodos de mayor carga de trabajo, aplicando criterios consistentes y evitando decisiones arbitrarias. Si varias solicitudes coinciden y no es posible mantener la cobertura del servicio, debe estudiar alternativas con las personas afectadas.

Si la solicitud supera el límite ordinario de 15 días laborables consecutivos, se solicita con menos de 15 días naturales de antelación, o requiere cualquier otra excepción a la política, no puede aprobarla por sí solo: debe remitirla a RR. HH. de España para su valoración, y la autorización de la excepción debe constar en el sistema corporativo correspondiente.

**Citations:**
- ES-006 v1.0 — 4. Gestión de vacaciones (`ES-006:1.0:4`)
- ES-001 v1.0 — 5. Aprobación y planificación del equipo (`ES-001:1.0:5`)
- ES-001 v1.0 — 8. Excepciones (`ES-001:1.0:8`)
- ES-006 v1.0 — 8. Excepciones y escalado (`ES-006:1.0:8`)
- ES-006 v1.0 — 3. Recepción y revisión de solicitudes (`ES-006:1.0:3`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-09 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, si un gasto de viaje va a superar los límites ordinarios de la política, ¿qué tiene que haber ocurrido antes de que se considere autorizado, y qué debo comprobar yo al revisar el caso?

**Expected answer summary:** Debe existir una autorización excepcional previa, documentada en los canales corporativos correspondientes; no se presume concedida por el hecho de que el viaje ya esté aprobado o el gasto ya se haya realizado (ES-005 §9). Al revisar el caso, debo identificar el concepto, el importe, el motivo de la excepción, la autorización y los justificantes pertinentes, colaborando con Finanzas cuando afecte a condiciones de personal (ES-007 §8).

**Actual answer (abstained=False):** Para que un gasto que supere los límites ordinarios de la política de viajes (ES-005) se considere autorizado, debe haberse obtenido una **autorización excepcional previa**. Esto no se presume concedida por el mero hecho de que el viaje haya sido aprobado o de que el gasto ya se haya realizado; la excepción debe quedar documentada en los canales corporativos correspondientes. Además, la aprobación previa del responsable directo para el viaje (que requiere motivo de negocio, destino, fechas y estimación de coste) no implica autorización automática de gastos que superen los límites.

Como responsable de RR. HH. al revisar el caso, según los principios de revisión aplicables (ES-007), debes:
1. Identificar la política vigente y la regla ordinaria afectada.
2. Confirmar que la solicitud pertenece al ámbito de España.
3. Revisar únicamente los antecedentes administrativos necesarios.
4. Verificar la justificación y los efectos operativos aportados, sin solicitar información sensible innecesaria.
5. Comprobar si existe un requisito legal o contractual que deba prevalecer sobre la política interna.
6. Determinar el nivel de autorización aplicable y documentar el resultado.

Además, al tratarse de gastos excepcionales, la revisión debe identificar el concepto, importe, motivo de la excepción, autorización y justificantes pertinentes, teniendo en cuenta que RR. HH. colabora con Finanzas en lo relativo a condiciones de personal, pero la validación económica se tramita por el circuito corporativo correspondiente. Los límites máximos de la política no se interpretan como importes garantizados. Las decisiones deben basarse en criterios objetivos y comparables, sin utilizar características personales protegidas ni información médica como criterios de conveniencia empresarial.

**Citations:**
- ES-007 v1.0 — 8. Gastos y desplazamientos excepcionales (`ES-007:1.0:8`)
- ES-005 v1.0 — 9. Excepciones y superación de límites (`ES-005:1.0:9`)
- ES-005 v1.0 — 3. Autorización y planificación del viaje (`ES-005:1.0:3`)
- ES-007 v1.0 — 3. Principios de revisión (`ES-007:1.0:3`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-10 — spain-hr (expected: answerable)

**Question:** Como responsable de RR. HH. en España, si un empleado solicita de forma recurrente teletrabajar un cuarto día cada semana además del régimen habitual de tres días, ¿qué tengo que comprobar antes de decidir, y una concesión puntual cambiaría su régimen habitual de forma permanente?

**Expected answer summary:** No, una excepción concedida para una semana no modifica automáticamente el régimen habitual ni crea una autorización permanente (ES-003 §6). Antes de decidir sobre una solicitud que supere el régimen ordinario de tres días semanales, debo comprobar la elegibilidad del puesto, las condiciones individuales aplicables, la valoración del responsable directo y las necesidades de coordinación del equipo (ES-007 §6).

**Actual answer (abstained=False):** Antes de decidir sobre una solicitud de un cuarto día de teletrabajo (por encima del régimen ordinario de 3 días semanales), debe tenerse en cuenta lo siguiente:

- La persona interesada debe plantearlo con antelación razonable a su responsable y seguirse el procedimiento de excepción aplicable [0].
- Al tratarse de una solicitud superior al régimen ordinario de 3 días semanales, requiere revisión excepcional: RR. HH. debe comprobar la elegibilidad del puesto, las condiciones individuales aplicables, la valoración del responsable y las necesidades de coordinación [1].
- La concesión depende de las circunstancias y de las aprobaciones necesarias; no debe comunicarse como aprobada antes de completar el proceso correspondiente [0].

En cuanto a si una concesión puntual cambia el régimen habitual de forma permanente: no. Una excepción concedida para una semana no modifica automáticamente el régimen habitual ni crea una autorización permanente [0]. Si la solicitud es de carácter recurrente (todas las semanas), los fragmentos disponibles no especifican el procedimiento concreto para ese caso continuado más allá del tratamiento de la excepción puntual, por lo que no puedo precisar con certeza cómo se gestionaría esa recurrencia específica.

**Citations:**
- ES-003 v1.0 — 6. Teletrabajo adicional y excepciones (`ES-003:1.0:7`)
- ES-007 v1.0 — 6. Excepciones de teletrabajo y flexibilidad (`ES-007:1.0:6`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-11 — spain-employee (expected: answerable)

**Question:** Si teletrabajo en España, ¿con qué tipo de equipo debo hacerlo, y puedo usar mi propio ordenador personal si tengo activada la autenticación en dos pasos?

**Expected answer summary:** Debo usar dispositivos corporativos y herramientas autorizadas; usar un portátil o una conexión segura no sustituye esa exigencia (ES-003 §7). Un dispositivo personal no está permitido para acceder a aplicaciones o datos corporativos, salvo que exista una excepción específica documentada y aprobada previamente por Seguridad de la Información — tener activada la autenticación en dos pasos no sustituye esa aprobación (GLB-002 §4).

**Actual answer (abstained=False):** Según ES-003, el trabajo remoto debe realizarse con dispositivos corporativos y herramientas autorizadas, de acuerdo con GLB-002 (Information Security Policy) [2]. En cuanto a usar un ordenador personal propio con autenticación en dos pasos activada: los fragmentos no lo permiten, ya que especifican que debe usarse equipamiento corporativo y herramientas autorizadas, y además aclaran que el uso de un portátil corporativo o una conexión segura no sustituye las autorizaciones organizativas o geográficas exigidas por la política [2]. No hay información que indique que un ordenador personal con autenticación en dos pasos sea una alternativa aceptada.

**Citations:**
- ES-003 v1.0 — 7. Equipamiento y seguridad de la información (`ES-003:1.0:8`)

**Evidence recall:** 1/2 (all_found=False)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-12 — spain-manager (expected: answerable)

**Question:** Como manager en España, un colaborador me comunica, sin haber avisado con antelación, que tiene que ausentarse por una emergencia familiar imprevista. ¿Estaba obligado a avisar con antelación en este caso, puedo exigirle que me explique el motivo médico o clínico, y qué debo hacer yo en ese momento?

**Expected answer summary:** No estaba obligado a avisar con antelación: no se exige una solicitud anticipada cuando la naturaleza de la emergencia lo impide (ES-002 §7). Tampoco puedo exigirle que explique el motivo médico o clínico: no debo pedir diagnósticos, informes clínicos ni explicaciones médicas detalladas. Como manager, debo confirmar la recepción de la comunicación y organizar la cobertura operativa razonable, informando a RR. HH. si resulta necesario para la tramitación administrativa (ES-006 §6).

**Actual answer (abstained=False):** No, no estaba obligado a avisar con antelación: ante una emergencia familiar imprevista, la prioridad es que la persona comunique la situación tan pronto como sea razonablemente posible, y no se exige solicitud anticipada cuando la naturaleza de la emergencia lo impida [0]. Esto es coherente con el principio general de que, si la ausencia es imprevista, basta con informar al responsable directo tan pronto como resulte razonablemente posible [1].

En cuanto a exigir explicaciones médicas o clínicas: no debe pedir diagnósticos, informes clínicos ni explicaciones médicas detalladas; los justificantes y documentos sensibles se gestionan exclusivamente mediante los canales autorizados de RR. HH. [2].

En ese momento, como responsable directo, debe organizar la cobertura operativa sin solicitar información privada innecesaria [0], confirmar la recepción de la comunicación y organizar la cobertura operativa razonable, informando a RR. HH. si resulta necesario para la tramitación administrativa correspondiente [2]. Además, la información que comparta con el resto del equipo debe limitarse a lo necesario para organizar el trabajo, sin revelar motivos privados de la ausencia [2]. Tenga en cuenta que la existencia de la emergencia no implica automáticamente descuento de vacaciones, y su duración o condición retributiva dependerá del supuesto aplicable, lo que evaluará RR. HH. [0].

**Citations:**
- ES-002 v1.0 — 7. Emergencias familiares (`ES-002:1.0:7`)
- ES-002 v1.0 — 3. Principios generales de comunicación (`ES-002:1.0:3`)
- ES-006 v1.0 — 6. Ausencias imprevistas y enfermedad (`ES-006:1.0:6`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-13 — england-employee (expected: answerable)

**Question:** In England, if I need to request annual leave with less notice than the ordinary 14 calendar days because of a specific personal circumstance, could that still be considered, and who is responsible for deciding on an exception like that?

**Expected answer summary:** Short-notice requests may be considered where circumstances justify them, although the ordinary notice period is an internal planning expectation and does not override statutory rights (EN-001 §4). England HR is responsible for interpreting the policy and assessing exceptions, together with the relevant line manager where appropriate, and any exception must be documented (EN-001 §12).

**Actual answer (abstained=True):** The retrieved policy fragments don't mention a standard 14 calendar days' notice requirement for annual leave, nor do they describe a process for granting exceptions to such a notice period. I don't have enough information in the provided material to answer this confidently.

**Citations:** none

**Evidence recall:** 0/2 (all_found=False)
**Outcome check:** matches_expected=False

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-14 — mexico-employee (expected: answerable)

**Question:** Antes de usar una herramienta de IA ya aprobada por la empresa para generar un primer borrador de un informe que incluye datos internos de rendimiento de mi equipo en México, ¿qué debo comprobar sobre ese tipo de información, y qué debo hacer con el contenido que genere la herramienta antes de compartirlo?

**Expected answer summary:** Debo comprobar que la información interna puede introducirse en esa herramienta concreta: no debe introducirse información interna en servicios no aprobados para ese uso, salvo que Seguridad de la Información haya autorizado expresamente esa categoría (GLB-002 §6). Antes de compartir el contenido generado, debo revisarlo en cuanto a exactitud, adecuación, confidencialidad y posible sesgo, ya que sigo siendo responsable de mis decisiones profesionales y de los resultados de mi trabajo (GLB-001 §7).

**Actual answer (abstained=False):** Aunque la herramienta de IA esté aprobada por la empresa, la aprobación de la herramienta no implica automáticamente la autorización para usar todas las categorías de información con ella. Debe comprobar la clasificación de los datos internos de rendimiento de su equipo: en general, la información Confidencial o Restringida no debe introducirse en servicios de IA no aprobados, y la información Interna debe evitarse en servicios no aprobados salvo autorización expresa de Seguridad de la Información; por lo tanto, debe verificar si existe un flujo de trabajo aprobado para ese tipo concreto de información antes de introducirla en la herramienta. Antes de compartir el contenido generado, debe revisarlo para verificar su exactitud, confidencialidad y el manejo adecuado del material fuente, ya que usted sigue siendo responsable de esa verificación y de sus decisiones profesionales respecto al resultado producido por la IA.

**Citations:**
- GLB-002 v1.0 — 6. Use of artificial intelligence tools (`GLB-002:1.0:6`)
- GLB-001 v1.0 — 7. Artificial intelligence and automated tools (`GLB-001:1.0:7`)

**Evidence recall:** 2/2 (all_found=True)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-15 — spain-employee (expected: abstain)

**Question:** Hace dos semanas tuve una comida de representación con un cliente en Madrid dentro de un viaje de trabajo. ¿Qué necesito para que ese gasto sea reembolsable, y ha sido ya aprobado y reembolsado mi gasto concreto?

**Expected answer summary:** —

**Actual answer (abstained=True):** Para que el gasto de la comida de representación con el cliente sea reembolsable necesitas: (1) autorización previa específica para ese gasto de representación, (2) poder identificar su finalidad profesional, y (3) aportar la documentación justificativa correspondiente. Además, debes presentar el gasto a través del canal corporativo autorizado dentro de los 15 días naturales posteriores a la finalización del viaje, acompañado del justificante que permita identificar el concepto, importe y fecha. En cuanto a tu caso concreto, los fragmentos disponibles no indican si tu gasto en particular ha sido autorizado, revisado o reembolsado; la presentación de una solicitud no equivale a su aceptación, ya que los importes se revisan conforme a la política y a las autorizaciones concedidas. No tengo información para confirmar si tu gasto específico ya ha sido aprobado o reembolsado.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-16 — england-employee (expected: abstain)

**Question:** I'm expecting a child and will need to be away from my role in England for a while. What family-related leave categories might apply to me, and exactly how long would I personally be entitled to be off in my case?

**Expected answer summary:** —

**Actual answer (abstained=True):** According to the policy, employees in England may have statutory rights to maternity, paternity, adoption, shared parental, parental bereavement, dependants' emergency leave, and other forms of protected time off, depending on their individual circumstances and current law. However, the fragments do not specify exact durations of entitlement for any of these leave types, as HR determines eligibility, documentation, and pay arrangements under the applicable rules on a case-by-case basis. I cannot tell you exactly how long you personally would be entitled to be off, since that depends on individual circumstances and legal rules not detailed in the available material — you should contact England HR to get your specific entitlement.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-17 — england-employee (expected: abstain)

**Question:** Does Northfern Technologies provide any life insurance benefit for employees in England?

**Expected answer summary:** —

**Actual answer (abstained=True):** The retrieved policy fragments do not mention any life insurance benefit for employees in England. I can't confirm whether such a benefit exists based on the available material.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-18 — mexico-employee (expected: abstain)

**Question:** ¿Northfern ofrece algún programa de préstamos personales sin intereses para empleados de México en dificultades económicas?

**Expected answer summary:** —

**Actual answer (abstained=True):** No encuentro información en los documentos proporcionados sobre un programa de préstamos personales sin intereses para empleados de México en dificultades económicas. Las políticas disponibles tratan sobre vacaciones y permisos (incluyendo un día de asuntos personales) y sobre teletrabajo y flexibilidad, pero no mencionan ningún beneficio de préstamo. No puedo responder con confianza a esta pregunta con la información disponible.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-19 — spain-employee (expected: abstain)

**Question:** Si tengo una ausencia que no encaja claramente en ninguna categoría administrativa habitual en España, ¿qué procedimiento sigue RR. HH. para decidir cómo se tramita, y cuándo consulta al área Legal?

**Expected answer summary:** —

**Actual answer (abstained=True):** Los fragmentos disponibles no incluyen esa información. Indican que las dudas sobre la clasificación de una ausencia y las circunstancias excepcionales deben dirigirse a Recursos Humanos de España, y que los procedimientos y decisiones internos (como los descritos en ES-006 y ES-007) son de acceso restringido y no forman parte de esta política de acceso general. No se detalla el procedimiento interno exacto que sigue RR. HH. para clasificar ausencias atípicas ni cuándo consulta al área Legal, por lo que no puedo responder con confianza a esa parte de la pregunta.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---

### eval-crag-20 — spain-manager (expected: abstain)

**Question:** Como manager en España, si un colaborador de México me pregunta si debe usar sus vacaciones pendientes antes de una fecha límite como el 31 de marzo, igual que en España, ¿qué le respondo sobre la regla aplicable en México?

**Expected answer summary:** —

**Actual answer (abstained=True):** No puedo responder con certeza. Los fragmentos disponibles (ES-001 y ES-006) solo describen la política de vacaciones aplicable en España, incluido el límite del 31 de marzo del año siguiente para días pendientes, pero no contienen información sobre la normativa o política de vacaciones aplicable en México. No debe asumirse que la regla española se aplica automáticamente a México; habría que consultar la política local correspondiente o a Recursos Humanos de México.

**Citations:** none

**Evidence recall:** n/a (no expected evidence for this question)
**Outcome check:** matches_expected=True

**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] citation_support=[ ] notes: ___

---
