# GUÍA DE LECTURA · scripts/demo.py
# Ejecuta una consulta de desarrollo y conserva la respuesta tal como llegó.
# --proveedor elige el recorrido: qwen (Transformers) o una ruta de curso.remote.
# Sin --proveedor se usa LLM_PROVIDER/LLM_MODEL de .env (por defecto, Claude por Anthropic).
# --adaptador activa LoRA con Qwen.
# --fewshot cambia los mensajes enviados, no entrena el modelo.
# La valoración compara con el objetivo y no modifica la respuesta generada.
# --salida guarda evidencia y rechaza sobrescribir un archivo existente.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
# Permite leer opciones de la terminal y generar ayuda del comando.
# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import argparse
import json
import time

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

import _bootstrap  # noqa: F401

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, assert_frozen, read_jsonl, validate_answer

# Rutas remotas/locales disponibles; la clave coincide con los valores de LLM_PROVIDER.
from curso.remote import PROVEEDORES


# Lee el caso y los argumentos, llama al proveedor y registra respuesta/valoración.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser(description="Un caso de desarrollo; no usa el test.")
    # --proveedor: qwen (Transformers local) o una ruta de curso.remote; sin valor, LLM_PROVIDER de .env.
    p.add_argument("--proveedor", choices=("qwen", *PROVEEDORES))
    # --modelo: ID del modelo en la ruta elegida; sustituye a LLM_MODEL.
    p.add_argument("--modelo")
    # --caso: ID de datos/desarrollo.jsonl que se consulta (DE-01 a DE-06).
    p.add_argument("--caso", default="DE-01")
    # --local-api: con LM Studio, API nativa (native) o interfaz compatible con OpenAI (openai).
    p.add_argument("--local-api", choices=("native", "openai"), default="native")
    # --fewshot: añade a los mensajes los cuatro ejemplos fijados de train.
    p.add_argument("--fewshot", action="store_true")
    # --adaptador: carpeta de un adaptador LoRA entrenado; solo se usa con --proveedor qwen.
    p.add_argument("--adaptador")
    # --salida: archivo JSON opcional para guardar el resultado; no sobrescribe uno existente.
    p.add_argument("--salida")
    # Argumentos de la terminal convertidos a atributos como args.caso o args.proveedor.
    args = p.parse_args()
    # Busca en datos/desarrollo.jsonl el caso indicado con --caso (por ejemplo, DE-04).
    # next(..., None) devuelve None si ningún caso coincide, en lugar de lanzar StopIteration.
    row = next(
        (
            x
            for x in read_jsonl(ROOT / "datos/desarrollo.jsonl")
            if x["id"] == args.caso
        ),
        None,
    )
    # Un ID inexistente termina con un mensaje de ayuda, no con una traza de Python.
    if row is None:
        # p.error imprime el uso del comando y el mensaje, y termina el programa (código 2).
        p.error(
            f"--caso {args.caso} no existe en datos/desarrollo.jsonl (DE-01 a DE-06)"
        )
    # --adaptador solo tiene sentido con Qwen local; en otra ruta se ignoraría sin avisar.
    if args.adaptador and args.proveedor != "qwen":
        # Termina con un mensaje de uso; no se consulta ningún modelo.
        p.error("--adaptador solo se usa con --proveedor qwen")
    # Nunca sobrescribe y lo comprueba ANTES de consultar: así no se gasta una llamada de pago
    # para acabar fallando al guardar.
    if args.salida and Path(args.salida).exists():
        # Termina antes de cualquier consulta; el archivo anterior queda intacto.
        p.error(
            f"--salida {args.salida} ya existe; elige otro archivo y conserva el anterior"
        )
    # Ruta Transformers: conserva protocolo y permite original, few-shot o adaptador LoRA.
    if args.proveedor == "qwen":
        # Comprueba hashes del experimento antes de consultar la condición Qwen.
        assert_frozen()
        # Importa Qwen solo en esta rama: las rutas remotas no necesitan torch ni transformers.
        from curso.qwen import generate, load_qwen

        # Carga la misma base y solo aplica adaptador cuando --adaptador contiene una ruta.
        model, tok, device = load_qwen(args.adaptador)
        # Consulta una incidencia de desarrollo, no los casos reservados de test.
        result = generate(model, tok, device, row["incidencia"], args.fewshot)
    # Ruta LM Studio: --local-api decide petición nativa o compatible.
    elif args.proveedor == "local":
        # Adaptador de LM Studio de curso/remote.py.
        from curso.remote import chat_local

        # native=True usa la API propia de LM Studio; --local-api openai usa la compatible.
        result = chat_local(
            row["incidencia"], args.modelo, args.fewshot, args.local_api == "native"
        )
    # Cualquier otra ruta, o la de .env si no se indica --proveedor.
    else:
        # Punto de entrada común a todos los proveedores remotos.
        from curso.remote import chat

        # Ruta de --proveedor o de .env; --modelo sustituye a LLM_MODEL.
        try:
            # Llamada real al proveedor: puede tardar y, en rutas de pago, consume saldo.
            result = chat(row["incidencia"], args.proveedor, args.modelo, args.fewshot)
        # Configuración incompleta (modelo, clave o URL): ayuda CLI en lugar de una traza.
        except ValueError as exc:
            # Muestra el problema como error de uso del comando y termina.
            p.error(str(exc))
    # Evidencia de un caso con entrada, objetivo, respuesta original, fecha y valoración.
    record = {
        # ID del caso de desarrollo, por ejemplo DE-04.
        "id": row["id"],
        # Texto que se envió al modelo.
        "incidencia": row["incidencia"],
        # Respuesta anotada con la que se compara.
        "objetivo": row["objetivo"],
        # Fecha y hora UTC de la consulta (formato ISO 8601).
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        # ** copia aquí todos los campos devueltos por el proveedor: respuesta, tokens, coste…
        **result,
        # Banderas del validador: JSON, esquema, categoría y prioridad.
        "valoracion": validate_answer(result["respuesta_original"], row["objetivo"]),
    }
    # Guardar es opcional; cuando se pide, se conserva una evidencia nueva sin sobrescribir otra.
    if args.salida:
        # Archivo indicado con --salida; ya se comprobó que no existía.
        path = Path(args.salida)
        # Crea la carpeta si falta; parents/exist_ok controlan subcarpetas y rutas ya existentes.
        path.parent.mkdir(parents=True, exist_ok=True)
        # Guarda el registro como JSON legible (indent=2) y con tildes sin escapar.
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    # Muestra el registro completo en la terminal, se haya guardado o no.
    print(json.dumps(record, ensure_ascii=False, indent=2))


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
