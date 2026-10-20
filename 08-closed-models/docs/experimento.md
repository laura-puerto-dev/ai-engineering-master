# Protocolo del experimento

Clasificar incidencias ficticias en acceso, facturacion, tecnico o consulta;
asignar alta/media/baja y redactar una o dos frases. Reglas en
`prompts/basico.txt`.

## Datos

Train: 240 registros, 60 por categoría, a partir de 40 situaciones iniciales
con seis variantes de prefijo. Validación y test: 30 cada uno. Desarrollo: 6.
Se comprueban IDs/textos/familias separados. La diversidad sintética es limitada.

`id` y `familia` son metadatos. Entrenamiento utiliza instrucciones, incidencia
y respuesta objetivo. Template común, thinking off y tokens sin duplicación.
Solo la completion aporta pérdida directa.

Validación se evalúa por época sin elegir automáticamente un checkpoint.
`config/experimento-congelado.json` registra hashes y revisión. No regenerar
ni ajustar después de leer test. Una variante requiere su propio experimento.

## Condiciones

S7, el mismo Qwen3-0.6B en local:

1. Qwen original con instrucciones básicas.
2. El mismo Qwen con cuatro ejemplos de train en cada consulta.
3. El mismo Qwen con LoRA y las instrucciones básicas.

LoRA: dos épocas, r=8, alpha=16, dropout=0.05 y configuración fija.
Comparar con Qwen3.5-4B cambiaría también el modelo.

S8 añade, con los mismos datos, test y validador:

4. Gemini base (`gemini-3.1-flash-lite`) en Google Cloud con instrucciones básicas.
5. Gemini ajustado en Google Cloud con train y validación, mismas instrucciones.
6. Claude con instrucciones básicas y los mismos cuatro ejemplos few-shot. Ruta del
   curso: Claude Haiku 5.5 (`claude-haiku-5-5`) por la API de Anthropic.

Condiciones adicionales, que no sustituyen a ninguna de las seis:
`remoto_basico` (cualquier ruta del `.env` con instrucciones básicas) y
`gemini_openrouter_demo` (Gemini por OpenRouter, demo histórica).

## Rutas remotas

Todas las rutas reciben el mismo `prompts/basico.txt`, los mismos ejemplos
cuando hay few-shot y un máximo de 180 tokens de salida. Sin reintentos: un fallo
de API queda como error en el denominador. Cada proveedor tiene parámetros
propios y el registro los conserva:

- Claude Haiku 5.5: instrucciones en `system`, `thinking` desactivado y sin
  `temperature`, que este modelo solo admite en su valor predeterminado; por eso
  sus respuestas no son deterministas.
- Gemini (Gemini API y Google Cloud): `systemInstruction`, temperatura 0 y
  `thinkingLevel` MINIMAL, iguales para base y ajustado.
- Chat Completions (OpenAI, OpenRouter y APIs compatibles): mensaje `system`;
  temperatura 0 salvo en OpenAI, cuyos modelos de razonamiento la rechazan. En
  OpenRouter, temperatura y razonamiento dependen de lo que admita cada modelo
  según su catálogo (`curso/remote.py:openrouter_settings`); lo enviado queda en
  `parametros_solicitados`.

Los ajustes de `LLM_TEMPERATURE` y `LLM_EXTRA_BODY` cambian el experimento y se
declaran con los resultados. Cada registro guarda ruta, modelo devuelto,
proveedor que respondió, motivo de parada, tokens, latencia y coste con su método.

## Métricas

JSON, esquema, categoría, prioridad y ambas etiquetas se miden por separado.
Una salida no interpretable y los fallos de API siguen en el denominador.
Originales conservados, sin JSON mode, tools que impongan formato, reparación
ni reintentos correctores.

La utilidad del texto necesita revisión humana. Los objetivos genéricos pueden
producir etiquetas correctas y respuestas poco útiles.
La API web serializa peticiones: su tiempo puede incluir cola. Coste desconocido
se conserva como null. Entrenamiento e inferencia se contabilizan por separado.

`resultados-referencia.json` contiene cifras de una ejecución anterior fechada.
Las nuevas se guardan por separado. LoRA no tiene que ganar; 30 casos no
establecen un ganador universal.
