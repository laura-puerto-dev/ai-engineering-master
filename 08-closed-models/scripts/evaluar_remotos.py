# GUÍA DE LECTURA · scripts/evaluar_remotos.py
# Evalúa modelos remotos con los mismos datos y validador de S7.
# claude_prompt y remoto_basico usan la ruta de .env (LLM_PROVIDER/LLM_MODEL) o de
# --proveedor/--modelo: por defecto, Claude Haiku 5.5 por la API de Anthropic.
# Gemini base/ajustado van por Google Cloud; la condición ajustada necesita su recurso.
# Un fallo permanece en los resultados y no se sustituye por otro modelo.
# Las llamadas remotas pueden consumir presupuesto; no se hacen al importar el archivo.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Permite leer opciones de la terminal y generar ayuda del comando.
# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import argparse, time

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, read_jsonl, assert_frozen, validate_answer, write_jsonl

# Elección de ruta, comprobación de credenciales, catálogo de OpenRouter y llamada al proveedor.
from curso.remote import chat, openrouter_model, require_credentials, route


# Condiciones con ruta fija: el par Gemini del ejercicio y la demo histórica por OpenRouter.
FIXED_ROUTES = {
    "gemini_base": ("google", "gemini-3.1-flash-lite"),
    "gemini_ajustado": ("google", None),
    "gemini_openrouter_demo": ("openrouter", "google/gemini-3.1-flash-lite"),
}


# Selecciona ruta y modelo remotos, recorre los casos y conserva un resultado por caso.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # --condicion: claude_prompt (few-shot) y remoto_basico (prompt básico) usan la ruta de .env;
    # gemini_base y gemini_ajustado van por Vertex AI; gemini_openrouter_demo, por OpenRouter.
    p.add_argument(
        "--condicion",
        choices=(
            "claude_prompt",
            "remoto_basico",
            "gemini_base",
            "gemini_ajustado",
            "gemini_openrouter_demo",
        ),
        required=True,
    )
    # --proveedor: ruta de claude_prompt/remoto_basico; sin ella se usa LLM_PROVIDER de .env.
    p.add_argument("--proveedor")
    # --modelo: ID del modelo en esa ruta; obligatorio para gemini_ajustado (recurso del tuning).
    p.add_argument("--modelo")
    # --salida: archivo JSONL nuevo donde se guardan los resultados (obligatorio).
    p.add_argument("--salida", required=True)
    # --split: partición evaluada; desarrollo para ensayar y test solo para la medida final.
    p.add_argument(
        "--split", choices=("desarrollo", "validacion", "test"), default="desarrollo"
    )
    # Argumentos de la terminal convertidos a atributos como args.condicion o args.salida.
    args = p.parse_args()
    # Manifiesto verificado que acompaña los resultados y conserva el protocolo exacto.
    frozen = assert_frozen()
    # Nunca sobrescribe: un resultado anterior es evidencia que se conserva.
    if Path(args.salida).exists():
        # Termina con un mensaje de uso antes de cualquier llamada.
        p.error(
            f"--salida {args.salida} ya existe; elige otro archivo y conserva el anterior"
        )
    # El recurso ajustado no se puede deducir: debe proceder de un entrenamiento Google real.
    if args.condicion == "gemini_ajustado" and not args.modelo:
        # Termina: sin recurso ajustado no hay modelo que consultar.
        p.error("Indica el recurso de modelo ajustado")
    # Ruta fija para Gemini; las demás condiciones admiten cualquier proveedor configurado.
    if args.condicion in FIXED_ROUTES:
        # Ruta y modelo fijos de la condición; el modelo es None en gemini_ajustado.
        provider, default_model = FIXED_ROUTES[args.condicion]
        # Validación previa: estas condiciones no cambian de proveedor.
        if args.proveedor and args.proveedor != provider:
            # Termina: la condición no admite otro proveedor.
            p.error(f"{args.condicion} usa siempre la ruta {provider}")
        # --modelo si se indica; si no, el modelo fijo de la condición.
        provider, model = provider, args.modelo or default_model
    # claude_prompt y remoto_basico: --proveedor/--modelo o, si faltan, la ruta de .env.
    else:
        # None en cualquiera de los dos hará que route() use .env.
        provider, model = args.proveedor, args.modelo
    # Resuelve y valida la ruta antes del lote: una configuración incompleta no genera 30 errores.
    try:
        # Normaliza el proveedor y completa el modelo desde .env si falta.
        provider, model = route(provider, model)
        # Comprueba que existe la clave (o el proyecto) de esa ruta, sin mostrarla.
        require_credentials(provider)
        # OpenRouter: un ID mal escrito se detecta aquí, en el catálogo gratuito, y no en 30 errores.
        if provider == "openrouter":
            # Busca el modelo en el catálogo; si no existe lanza ValueError con el motivo.
            openrouter_model(model)
    # Ruta desconocida, modelo ausente, credencial ausente o ID inexistente en OpenRouter.
    except ValueError as exc:
        # Termina con un mensaje de uso antes de la primera llamada.
        p.error(str(exc))
    # claude_prompt recibe los cuatro ejemplos few-shot fijados; el resto, el prompt básico.
    fewshot = args.condicion == "claude_prompt"
    # Resultados acumulados, incluyendo errores, para conservar un caso por entrada.
    results = []
    # Recorre cada registro de la partición elegida; conserva el ID para relacionar entradas y resultados.
    for row in read_jsonl(ROOT / f"datos/{args.split}.jsonl"):
        # try/except: un fallo en un caso se registra y el lote continúa.
        try:
            # Misma ruta y modelo en todos los casos del lote.
            result = chat(row["incidencia"], provider, model, fewshot)
            # Tipo de fallo del caso; None indica que la petición/generación terminó sin esa excepción.
            error = None
        # Exception captura cualquier error del caso (HTTP, red, formato…); Ctrl+C sí detiene el lote.
        except Exception as exc:
            # Conserva el fallo sin respuesta/tiempo/coste inventados; el tipo de excepción identifica el error.
            result = {
                # Sin respuesta: no se inventa texto.
                "respuesta_original": None,
                # Tiempo y coste desconocidos (None, no 0).
                "latencia_s": None,
                "coste_usd": None,
                # Modelo y ruta que se intentaron usar.
                "model": model,
                "ruta": provider,
            }
            # Nombre de la excepción, por ejemplo RuntimeError; el caso sigue en el denominador.
            error = type(exc).__name__
        # Guarda original, objetivo, fallo y fecha con el mismo manifiesto utilizado para el resto del lote.
        results.append(
            {
                # ID del caso.
                "id": row["id"],
                # Condición evaluada.
                "condicion": args.condicion,
                # Partición de donde sale el caso.
                "split": args.split,
                # Manifiesto congelado: identifica datos, prompt y modelo de S7.
                "experimento": frozen,
                # Texto enviado al modelo.
                "incidencia": row["incidencia"],
                # Respuesta anotada con la que se compara.
                "objetivo": row["objetivo"],
                # Campos devueltos por el proveedor (respuesta, tokens, coste, modelo, ruta…).
                **result,
                # Nombre de la excepción o None.
                "error": error,
                # Fecha y hora UTC del caso.
                "fecha": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                # Banderas del validador; un error cuenta como respuesta inválida.
                "valoracion": validate_answer(
                    result.get("respuesta_original"), row["objetivo"]
                ),
            }
        )
        # Reescribe el JSONL tras cada caso: si el proceso se corta, lo completado queda guardado.
        write_jsonl(args.salida, results)
        # Progreso en la terminal: ID, condición y error (None si fue bien).
        print(row["id"], args.condicion, "error=" + str(error), flush=True)


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
