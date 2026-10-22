# Comparación S7/S8

Muestra sintética de 30 casos por condición. Sin reparación ni reintentos correctores.

| Condición | Modelo · ruta | Casos | JSON | Categoría | Prioridad | Ambas | Mediana s | Coste USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| qwen_base | Qwen/Qwen3-0.6B | 30 | 30 | 14 | 6 | 3 | 1.5147464999754447 | No disponible |
| qwen_fewshot | Qwen/Qwen3-0.6B | 30 | 30 | 15 | 20 | 11 | 1.320253700017929 | No disponible |
| qwen_lora | Qwen/Qwen3-0.6B | 30 | 30 | 28 | 29 | 28 | 2.3502741499978583 | No disponible |
| gemini_base | projects/thepower-s8-gemini-512218/locations/eu/publishers/google/models/gemini-3.1-flash-lite · google | 30 | 30 | 26 | 30 | 26 | 1.4157622999919113 | No disponible |
| gemini_ajustado | projects/183729570563/locations/eu/endpoints/4602397344195936256 · google | 30 | 30 | 25 | 30 | 25 | 2.2271958000201266 | No disponible |
| claude_prompt | claude-haiku-5-5 · anthropic | 30 | 30 | 25 | 30 | 25 | 1.0842101000016555 | 0.0032698000000000002 |

Las filas sin ejecución permanecen pendientes. remoto_basico y gemini_openrouter_demo
son condiciones adicionales; no sustituyen la pareja Google base/ajustado.
