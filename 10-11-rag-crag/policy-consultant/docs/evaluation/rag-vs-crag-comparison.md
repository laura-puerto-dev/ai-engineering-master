# RAG vs. CRAG — Informe comparativo final (Fase 4, sesión 11)

## 1. Objetivo y metodología

Comparar el RAG baseline del módulo 10 con la configuración congelada de CRAG (Fase 3C) sobre un dataset nuevo e independiente de 20 preguntas (`docs/evaluation/crag-evaluation-questions.yaml`: 14 respondibles + 6 que requieren abstención), nunca usado para calibrar ninguno de los dos sistemas.

Ambos sistemas se ejecutaron una sola vez cada uno, sobre el mismo corpus, los mismos embeddings y los mismos perfiles/restricciones RLS, sin modificar sus prompts, modelos ni parámetros. Las respuestas esperadas del dataset se usaron **exclusivamente** para puntuar los resultados después de ejecutar cada sistema — nunca como entrada al pipeline.

Esta revisión distingue explícitamente tres cosas distintas, que no deben confundirse:

1. **Coincidencia con el resultado esperado** (¿contestó cuando debía contestar, abstuvo cuando debía abstener?) — métrica automática, estructural.
2. **Validez estructural de las citas** (¿la cita apunta a un fragmento realmente recuperado/entregado al generador?) — métrica automática, estructural. **No implica que la cita respalde realmente la afirmación concreta a la que acompaña.**
3. **Corrección y completitud factual** (¿la respuesta es correcta, cubre los aspectos exigidos, y las citas respaldan de verdad lo que afirman?) — juicio manual, el único de los tres que requiere leer el texto real de la política y la respuesta generada.

Fuentes usadas para la revisión manual: `docs/evaluation/crag-evaluation-questions.yaml`, `docs/evaluation/rag-final-results.json`, `docs/evaluation/crag-final-results.json`, y el texto original de los documentos en `data/corpus/`.

## 2. Configuración de ambos sistemas

| | RAG baseline | CRAG |
|---|---|---|
| Embeddings | BGE-M3, rev. `5617a9f6...` | BGE-M3, rev. `5617a9f6...` (idéntica) |
| Candidatos por recuperación | `top_k=5` | `top_k=10` (antes del reranking) |
| Reranking | — | Qwen3-Reranker-0.6B local |
| Recuperaciones internas | 1 (fija) | hasta `MAX_RETRIEVALS=3` (1 inicial + hasta 2 reformulaciones) |
| Evaluador de evidencia | — | Claude Sonnet 5 (`effort="medium"`, sin `disable_thinking`) |
| Reformulador | — | Claude Sonnet 5 (`effort="medium"`, sin `disable_thinking`) |
| Generador | Claude Sonnet 5, `disable_thinking=True` | Claude Sonnet 5, `disable_thinking=True` (**idéntico** al baseline) |
| Perfiles / RLS | `web.app.DEMO_PROFILES`, mismas restricciones | idéntico |

La única diferencia de configuración real entre ambos es la arquitectura de recuperación (`top_k`, reranking, ciclo correctivo); el generador final es exactamente el mismo modelo con la misma configuración en los dos sistemas.

## 3. Resultados automáticos

| Métrica | RAG | CRAG |
|---|---|---|
| Respondibles contestadas | 13/14 | 14/14 |
| Abstenciones correctas | 6/6 | 6/6 |
| Falsas abstenciones | 1 (eval-crag-13) | 0 |
| Respuestas cuando se esperaba abstención | 0 | 0 |
| Coincidencia total con el resultado esperado | 19/20 | 20/20 |
| Cobertura de evidencia esperada (micro-promediada) | 0.857 (18/21 chunks) | 0.952 (20/21 chunks) |
| Citas estructuralmente válidas | 100% (26/26) | 100% (30/30; también 100% desde el contexto final entregado al generador) |
| Errores técnicos | 0 | 0 |
| Latencia media / mediana / máx | no instrumentada (ver §7) | 26.5s / 22.2s / 46.3s |
| Recuperaciones internas | 1 por pregunta (fijo) | media 1.7; distribución: 13 preguntas con 1, 7 con 3 |
| Llamadas de evaluación de evidencia (grader) | — | **34** (13×1 + 7×3) |
| Llamadas de reformulación | — | **14** (7 preguntas × 2 reformulaciones cada una) |
| Llamadas al generador de respuesta | 20 (todas las preguntas, incluidas las 6 abstenciones) | **14** (solo las respondibles; las 6 abstenciones de CRAG nunca llaman al generador) |
| Rutas del grader sobre esas 34 llamadas | — | `sufficient`=14, `ambiguous`=12, `insufficient`=8 |
| Divergencia ruta cruda del grader vs. ruta efectiva | — | 0 casos |

El número de llamadas no equivale a coste económico medido: no se ha registrado el gasto real de esta ejecución, y la facturación depende además de effort/tokens de entrada y salida de cada llamada, no solo del recuento de llamadas.

## 4. Resultados de la revisión manual

Clasificación por pregunta: **correcta** (cubre todos los aspectos exigidos, sin errores), **incompleta** (conclusión correcta pero omite un aspecto exigido) o **incorrecta** (conclusión equivocada o ausencia de respuesta cuando se esperaba una).

| Sistema | Correctas | Incompletas | Incorrectas |
|---|---|---|---|
| RAG | 17/20 | 2 (eval-crag-11, eval-crag-14) | 1 (eval-crag-13) |
| CRAG | 19/20 | 1 (eval-crag-11) | 0 |

Ninguna cita, en ninguno de los dos sistemas, resultó **no respaldar** la afirmación a la que acompañaba (0 casos de cita estructuralmente válida pero factualmente no respaldada). La evidencia alternativa a la prevista en el dataset se aceptó cuando realmente permitía fundamentar la respuesta (ver eval-crag-11 en §6).

Hallazgo transversal no anticipado en el dataset: en las 4 preguntas de abstención donde ya existía evidencia general relevante antes de abstener (eval-crag-15, 16, 19, 20), la respuesta de CRAG es siempre el mensaje fijo de `crag.abstain_node` ("No se encontró evidencia suficiente para responder con garantías." / "Not enough evidence was found to answer with confidence.", `src/policy_consultant/language.py`), sin explicar nada — por diseño, `abstain_node` nunca llama al generador. RAG, en cambio, sí llama siempre al generador, que redacta una explicación del motivo de la abstención apoyada en lo que vio (sin inventar el dato que falta). El resultado automático ("abstención correcta") es idéntico en ambos casos; la utilidad de la respuesta para la persona que pregunta no lo es.

## 5. Tabla comparativa de las 20 preguntas

| ID | Categoría | Esperado | RAG (outcome / revisión) | CRAG (outcome / revisión) |
|---|---|---|---|---|
| eval-crag-01 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-02 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-03 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-04 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-05 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-06 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-07 | direct_evidence | answerable | ✅ correcta | ✅ correcta |
| eval-crag-08 | multi_fragment | answerable | ✅ correcta | ✅ correcta |
| eval-crag-09 | multi_fragment | answerable | ✅ correcta | ✅ correcta |
| eval-crag-10 | multi_fragment | answerable | ✅ correcta (con matiz, ver nota) | ✅ correcta |
| **eval-crag-11** | multi_fragment | answerable | ⚠️ **incompleta** | ⚠️ **incompleta** |
| eval-crag-12 | multi_fragment | answerable | ✅ correcta | ✅ correcta |
| **eval-crag-13** | multi_fragment | answerable | ❌ **incorrecta (falsa abstención)** | ✅ **correcta** |
| **eval-crag-14** | multi_fragment | answerable | ⚠️ **incompleta** | ✅ **correcta** |
| eval-crag-15 | partially_answerable | abstain | ✅ correcta, informativa | ✅ correcta, no informativa |
| eval-crag-16 | partially_answerable | abstain | ✅ correcta, informativa | ✅ correcta, no informativa |
| eval-crag-17 | no_information | abstain | ✅ correcta | ✅ correcta |
| eval-crag-18 | no_information | abstain | ✅ correcta | ✅ correcta |
| eval-crag-19 | access_restricted | abstain | ✅ correcta, informativa | ✅ correcta, no informativa |
| eval-crag-20 | access_restricted | abstain | ✅ correcta, informativa | ✅ correcta, no informativa |

Nota eval-crag-10: la respuesta de RAG añade un matiz honesto ("los fragmentos no especifican el procedimiento para una solicitud recurrente") que CRAG no incluye; no se penaliza porque el texto real de ES-003 §6 sí generaliza la regla ("una excepción concedida para una semana no modifica automáticamente el régimen habitual") a cualquier frecuencia, así que la respuesta confiada de CRAG tampoco sobre-afirma.

## 6. Casos relevantes

### eval-crag-11 — un fallo de recuperación compartido, y una valoración de suficiencia de CRAG retrospectivamente insuficiente

La pregunta pide dos aspectos: qué equipo usar para teletrabajar, y si un dispositivo personal con 2FA es aceptable. El segundo aspecto exige mencionar que **sí existe** una vía de excepción (documentada y aprobada previamente por Seguridad de la Información, GLB-002 §4) para usar un dispositivo personal.

**Ambos sistemas omiten esa excepción**, y ambos comparten la misma causa de fondo: `GLB-002:1.0:4` nunca aparece entre los 5 candidatos de RAG ni entre los 10 candidatos reordenados de CRAG en el único intento que CRAG ejecutó para esta pregunta. Eso es un fallo de recuperación, no una diferencia entre los dos sistemas.

Pero hay un segundo hecho, propio solo de CRAG, que RAG no tiene un paso equivalente para cometer: el grader declaró explícitamente `route="sufficient"` con `missing_aspects=[]`. Con `ES-003:1.0:8` + `ES-004:1.0:10` (una ayuda de equipamiento que también dice textualmente que "no autoriza a utilizar dispositivos personales... para acceder a información corporativa") delante, esa valoración es comprensible — nada en ese conjunto concreto señalaba que faltara algo. Pero evaluada retrospectivamente contra el corpus completo (donde `GLB-002:1.0:4` sí existe), esa declaración de suficiencia fue insuficiente: afirmó estar completa una respuesta que no lo estaba. Al alcanzarse `sufficient` en el primer intento (`retrieval_count=1`), el ciclo correctivo nunca tuvo ocasión de reformular y buscar más allá de ese primer conjunto. RAG, al no declarar nunca una suficiencia explícita, no incurre en este segundo problema — simplemente responde con lo que recuperó, sin afirmar que fuera bastante.

Se aceptó `ES-004:1.0:10` como evidencia alternativa legítima para CRAG (realmente respalda la conclusión "no se permite dispositivo personal"), consistente con la instrucción de aceptar evidencia distinta de la prevista cuando fundamenta la respuesta — pero la respuesta sigue siendo incompleta porque ninguna evidencia usada menciona la excepción.

### eval-crag-13 — recuperación de evidencia nueva vía reformulación, con cambio de criterio de suficiencia

RAG (`top_k=5`) nunca recupera `EN-001:1.0:4` ni `EN-001:1.0:12` y abstiene incorrectamente (expected_outcome=answerable). CRAG:

- **Intento 1:** candidatos incluyen `EN-001:1.0:4` (se conserva) pero no `EN-001:1.0:12`; ruta `ambiguous`, falta "quién decide la excepción".
- **Intento 2** (tras reformular hacia "short-notice annual leave exception approval process England line manager HR criteria"): `EN-001:1.0:12` aparece por primera vez entre los candidatos y se conserva junto al anterior; ruta sigue `ambiguous` — el evaluador juzga que la sección 12 ("exceptions" en general) no confirma con suficiente explicitud quién decide las solicitudes de preaviso corto en el día a día, frente a excepciones de política más amplias.
- **Intento 3** (reformulación más específica: "who approves short-notice annual leave requests England line manager versus HR decision authority"): misma evidencia ya conservada (`EN-001:1.0:4` + `EN-001:1.0:12`, sin candidatos nuevos), pero ahora el evaluador concluye `sufficient` — el cambio de criterio entre el intento 2 y el 3 es sobre **la misma evidencia**, no sobre evidencia nueva; lo que cambió fue la lectura del evaluador sobre si esa evidencia ya respondía con suficiente explicitud.

La respuesta final es correcta y completa, y verificada contra el texto real de EN-001 §4 y §12. Demuestra que, en este caso concreto, la reformulación permitió recuperar evidencia nueva y necesaria (`EN-001:1.0:12`) que la recuperación inicial no encontró. No se trata de un experimento de ablación controlado, así que esto no debe leerse como que aísla de forma concluyente el efecto del ciclo correctivo frente a otras diferencias entre los dos sistemas (empezando por `top_k`) — es evidencia de que el mecanismo funcionó aquí, no una medición de cuánto explica por sí solo la diferencia global de resultados.

### eval-crag-14 — mismas citas, completitud distinta

Ambos sistemas citan exactamente `GLB-001:1.0:7` + `GLB-002:1.0:6`. RAG, pese a citar `GLB-001:1.0:7` (que menciona explícitamente "potential bias" y "appropriateness"), redacta su respuesta reproduciendo solo el lenguaje más estrecho de `GLB-002:1.0:6` ("exactitud, confidencialidad y manejo adecuado del material fuente") y omite sesgo y adecuación del contenido generado. CRAG cubre los cuatro elementos (precisión, idoneidad, confidencialidad, posibles sesgos) explícitamente.

Esto es una diferencia real de completitud en la generación, no de recuperación: ambos sistemas citaron exactamente los mismos dos chunks. No puede atribuirse a que el evaluador de CRAG rastree `covered_aspects`/`missing_aspects` antes de generar: esos campos no se entregan al generador (`crag.answer_node` solo le pasa la pregunta y los chunks conservados, igual que `rag.answer_question` le pasa la pregunta y los chunks recuperados), así que esa vía causal concreta queda descartada. Sí hay una diferencia verificada en el contexto que cada generador recibió: RAG (`top_k=5`) le entregó 5 chunks, incluidos tres ajenos a la pregunta (`MX-002:1.0:8`, `GLB-002:1.0:5`, `GLB-001:1.0:6`), mientras que CRAG solo le entregó los 2 chunks relevantes ya filtrados por el evaluador. Que ese mayor "ruido" de contexto en RAG, o simple variabilidad entre llamadas reales a Claude, sea la causa de la omisión son explicaciones posibles, no una causa aislada o confirmada con este dataset.

## 7. Limitaciones metodológicas

- **Dataset reducido y una sola ejecución por sistema:** 20 preguntas, sin repeticiones. Ninguna proporción (19/20, 20/20, etc.) debe tratarse como una tasa de error estimada con precisión estadística.
- **`top_k` distinto por diseño (RAG=5, CRAG=10 antes de reranking):** la mejora de cobertura de CRAG no puede atribuirse únicamente al ciclo correctivo — una parte de la ventaja observada en casos de un solo intento (p. ej. eval-crag-08 a eval-crag-12, eval-crag-14) podría explicarse simplemente por partir de más candidatos, no por reformular. eval-crag-13 es el caso que más claramente muestra el efecto de la reformulación en sí (evidencia nueva solo aparece tras reformular, en el intento 2), pero no se ha realizado un experimento de ablación controlado (p. ej. CRAG con `top_k=5`, o RAG con `top_k=10`) que permita aislar ese efecto del resto de diferencias entre los dos sistemas.
- **Ausencia de medición de latencia en el RAG baseline:** `run_evaluation.py` nunca ha instrumentado tiempo por pregunta; no se puede comparar latencia RAG vs. CRAG con este dataset.
- **Variabilidad del evaluador de suficiencia:** el propio caso eval-crag-13 muestra que el evaluador cambia de criterio (`ambiguous`→`sufficient`) sobre la misma evidencia entre dos intentos sucesivos. No hay suficientes repeticiones de esta pregunta (ni de ninguna otra) para estimar con qué frecuencia una repetición reproduciría la misma secuencia de rutas o el mismo resultado final.
- **Coste adicional de CRAG, medido en número de llamadas, no en coste económico:** sobre las 20 preguntas, CRAG hizo 34 llamadas de evaluación de evidencia y 14 de reformulación, además de 14 llamadas al generador (solo en las respondibles: las 6 abstenciones de CRAG nunca llaman al generador); RAG hizo 20 llamadas al generador (una por pregunta, incluidas las abstenciones) y ninguna de evaluación o reformulación. No se ha registrado el gasto económico real de esta ejecución (depende de effort y de tokens de entrada/salida, no solo del número de llamadas), así que esta comparación de llamadas no debe leerse como una comparación de coste medido.
- **La cobertura de los chunks esperados no equivale a suficiencia factual:** eval-crag-11 cubre 1/2 chunks esperados en ambos sistemas y aun así ambas respuestas son incompletas por el mismo motivo real (falta la excepción), no por casualidad estadística.
- **La validez estructural de una cita no garantiza que respalde la afirmación:** en este dataset no se observó ningún caso de cita estructuralmente válida pero no respaldada, pero esa ausencia es una observación de esta muestra, no una propiedad garantizada del sistema.

## 8. Conclusiones

Sobre este dataset de 20 preguntas, en esta única ejecución:

- CRAG igualó o superó a RAG en todas las métricas automáticas de coincidencia con el resultado esperado (20/20 vs. 19/20) y en cobertura de evidencia (0.952 vs. 0.857).
- La revisión manual confirma una ventaja real de CRAG en 2 de las 3 preguntas señaladas para atención especial (eval-crag-13, recuperación genuina vía reformulación; eval-crag-14, mayor completitud de la respuesta generada con la misma evidencia).
- En la tercera (eval-crag-11), ambos sistemas comparten el mismo hueco de recuperación de fondo (`GLB-002:1.0:4` nunca llegó a ninguno de los dos), pero solo CRAG tiene un paso adicional que falló: una declaración explícita de `sufficient` que, contra el corpus completo, era retrospectivamente insuficiente — comprensible dada la evidencia que el grader tenía delante, pero insuficiente igualmente. Al declararse sufficient en el primer intento, el ciclo correctivo nunca llegó a reformular para intentar corregirlo.
- Las abstenciones de CRAG, aunque siempre correctas en el resultado, son sistemáticamente menos informativas que las de RAG cuando ya existía evidencia parcial relevante — un coste de diseño (seguridad frente a utilidad) que vale la pena documentar para el portfolio, no un defecto a corregir sin más en esta fase.
- **No se puede generalizar** que CRAG sea "mejor" que RAG a partir de este dataset: la diferencia de `top_k` entre ambos sistemas limita cuánta de la mejora observada es atribuible al ciclo correctivo en sí frente a simplemente partir de más candidatos. eval-crag-13 demuestra que la reformulación recuperó evidencia nueva y necesaria que la búsqueda inicial no encontró, pero es un único ejemplo, no un experimento de ablación controlado, así que no permite aislar de forma concluyente cuánto del resultado global se debe al ciclo correctivo en sí.

Estos resultados y limitaciones son los que alimentarán el README e informe final de la Fase 5 — no se han ampliado aquí más allá de lo que este dataset concreto permite afirmar.
