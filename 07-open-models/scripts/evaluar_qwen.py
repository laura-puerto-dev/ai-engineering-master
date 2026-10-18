# GUÍA DE LECTURA · scripts/evaluar_qwen.py
# Ejecuta un lote local en una condición: básico, few-shot o LoRA.
# Cada caso conserva entrada, objetivo, salida, configuración y valoración.
# Una excepción queda registrada y cuenta dentro del lote; no se reintenta para mejorar cifras.
# El archivo se actualiza tras cada caso para conservar lo ya completado.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Permite leer opciones de la terminal y generar ayuda del comando.
import argparse

# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import time

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, assert_frozen, read_jsonl, validate_answer, write_jsonl


# Recorre una partición con la condición Qwen elegida y guarda originales y errores.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # --condicion: qwen_base (prompt básico), qwen_fewshot (más cuatro ejemplos) o qwen_lora (base + LoRA).
    p.add_argument(
        "--condicion", choices=("qwen_base", "qwen_fewshot", "qwen_lora"), required=True
    )
    # --split: partición evaluada; desarrollo para ensayar y test solo para la medida final.
    p.add_argument(
        "--split", choices=("desarrollo", "validacion", "test"), default="desarrollo"
    )
    # --adaptador: carpeta del adaptador LoRA entrenado; solo se usa con qwen_lora.
    p.add_argument("--adaptador", default=str(ROOT / "modelos/lora-soporte"))
    # --salida: archivo JSONL nuevo donde se guardan los resultados (obligatorio).
    p.add_argument("--salida", required=True)
    # Argumentos de la terminal convertidos a atributos como args.condicion o args.salida.
    args = p.parse_args()
    # Manifiesto verificado que acompaña los resultados y conserva el protocolo exacto.
    frozen = assert_frozen()
    # Nunca sobrescribe: un resultado anterior es evidencia que se conserva.
    if Path(args.salida).exists():
        # Termina con un mensaje de uso antes de cargar el modelo.
        p.error(
            f"--salida {args.salida} ya existe; elige otro archivo y conserva el anterior"
        )
    # qwen_lora necesita un adaptador entrenado: sin sus archivos se detiene antes de cargar Qwen.
    adapter_ready = all(
        (Path(args.adaptador) / name).exists()
        for name in ("adapter_config.json", "adapter_model.safetensors")
    )
    # Solo qwen_lora necesita el adaptador; base y few-shot usan la base sola.
    if args.condicion == "qwen_lora" and not adapter_ready:
        # Termina con un mensaje que indica cómo crear el adaptador.
        p.error(
            f"No hay adaptador en {args.adaptador}; entrénalo con scripts/entrenar_lora.py"
        )
    # Importa Qwen tras validar los argumentos: un error de opciones no espera a cargar torch.
    from curso.qwen import load_qwen, generate

    # Carga el adaptador solo para qwen_lora; las otras dos condiciones mantienen la base original.
    model, tokenizer, device = load_qwen(
        args.adaptador if args.condicion == "qwen_lora" else None
    )
    # Resultados acumulados, incluyendo errores, para conservar un caso por entrada.
    results = []
    # Recorre cada registro de la partición elegida; conserva el ID para relacionar entradas y resultados.
    for row in read_jsonl(ROOT / f"datos/{args.split}.jsonl"):
        # try/except: un fallo en un caso se registra y el lote continúa con el siguiente.
        try:
            # Respuesta original, tokens, tiempo y parámetros de esta generación.
            output = generate(
                model,
                tokenizer,
                device,
                row["incidencia"],
                args.condicion == "qwen_fewshot",
            )
            # Tipo de fallo del caso; None indica que la petición/generación terminó sin esa excepción.
            error = None
        # Exception captura cualquier error del caso (memoria, tokenizer…); Ctrl+C sí detiene el lote.
        except Exception as exc:
            # Cualquier fallo queda registrado sin respuesta, tiempo ni coste inventados.
            output = {"respuesta_original": None, "latencia_s": None, "coste_usd": None}
            # Nombre de la excepción (por ejemplo, RuntimeError); el caso sigue en el denominador.
            error = type(exc).__name__
        # Conserva un resultado por caso incluso si hubo excepción; el objetivo permite calcular aciertos.
        results.append(
            {
                # ID del caso de la partición.
                "id": row["id"],
                # Condición evaluada (qwen_base, qwen_fewshot o qwen_lora).
                "condicion": args.condicion,
                # Partición de donde sale el caso.
                "split": args.split,
                # Texto enviado al modelo.
                "incidencia": row["incidencia"],
                # Respuesta anotada con la que se compara.
                "objetivo": row["objetivo"],
                # Fecha y hora UTC del caso.
                "fecha": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                # Manifiesto congelado: identifica datos, prompt y modelo usados.
                "experimento": frozen,
                # Carpeta del adaptador, solo en qwen_lora.
                "adaptador": args.adaptador if args.condicion == "qwen_lora" else None,
                # Campos devueltos por generate (respuesta, tokens, latencia…) o los vacíos del error.
                **output,
                # Nombre de la excepción o None.
                "error": error,
                # Banderas del validador; un error cuenta como respuesta inválida.
                "valoracion": validate_answer(
                    output.get("respuesta_original"), row["objetivo"]
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
