# GUÍA DE LECTURA · scripts/gemini_tuning.py
# Cuatro acciones distintas: preparar, subir datos, crear tuning y consultar estado.
# Preparar solo describe el trabajo; las otras acciones acceden a Google Cloud.
# Train y validación se suben; test queda fuera del trabajo de entrenamiento.
# Proyecto, bucket y presupuesto deben ser explícitos.
# El presupuesto anotado es una comprobación local, no un límite de gasto del proveedor.

"""Preparar/consultar tuning; crear exige proyecto, bucket y presupuesto explícitos."""

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Permite leer opciones de la terminal y generar ayuda del comando.
# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
# Lee configuración del entorno y ajusta opciones del proceso.
# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import argparse, json, os, time

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, assert_frozen

# Cliente Vertex AI y lectura de .env definidos en curso/remote.py.
from curso.remote import google_client, load_config


# Valida proyecto y bucket y devuelve la especificación offline de tuning.
# No consulta Google, no crea recursos y nunca incluye el archivo de test.
def job_spec(project, bucket):
    # Sin proyecto o bucket no se puede describir dónde se entrenaría.
    if not project or not bucket:
        # Detiene el proceso con un mensaje claro.
        raise ValueError("Proyecto del curso y bucket son obligatorios")
    # Se espera un ID como mi-proyecto-123, no una URL de la consola.
    if "/" in project:
        # Detiene el proceso: se esperaba un ID.
        raise ValueError("Usa ID de proyecto, no URL")
    # Acepta nombre simple o gs://nombre, retirando únicamente prefijo y barras externas.
    bucket = bucket.removeprefix("gs://").strip("/")
    # Solo el nombre del bucket: la carpeta thepower-s7-s8/ la fija el script.
    if "/" in bucket:
        # Detiene el proceso: la carpeta dentro del bucket la decide el script.
        raise ValueError("Usa nombre de bucket sin subcarpetas")
    # Receta fija: región del tuning, modelo base, rutas gs:// de train y validación,
    # 2 épocas, adaptador de tamaño 8 y región donde se servirá el modelo ajustado.
    return {
        # Proyecto Google Cloud del laboratorio.
        "project": project,
        # Región donde se ejecuta el trabajo de tuning.
        "location": "europe-west4",
        # Modelo base que se ajusta.
        "base_model": "gemini-3.1-flash-lite",
        # Archivos de train y validación en el bucket; test nunca aparece aquí.
        "train_uri": f"gs://{bucket}/thepower-s7-s8/train.jsonl",
        "validation_uri": f"gs://{bucket}/thepower-s7-s8/validacion.jsonl",
        # Dos recorridos completos por train, como la receta LoRA de S7.
        "epochs": 2,
        # Tamaño del adaptador que entrena Google, comparable al rango 8 de la receta LoRA de S7.
        "adapter_size": 8,
        # Multirregión de consulta: base y ajustado se sirven por eu.
        # El trabajo y su estado se consultan en europe-west4.
        "serving_location": "eu",
    }


# Construye la configuración con los tipos reales del SDK, también para el ensayo offline.
def tuning_config(spec):
    from google.genai import types

    # google-genai 1.42 no admite el entero 8: espera AdapterSize.ADAPTER_SIZE_EIGHT.
    # La receta conserva su tamaño numérico en la especificación y lo traduce aquí.
    sizes = {
        1: types.AdapterSize.ADAPTER_SIZE_ONE,
        2: types.AdapterSize.ADAPTER_SIZE_TWO,
        4: types.AdapterSize.ADAPTER_SIZE_FOUR,
        8: types.AdapterSize.ADAPTER_SIZE_EIGHT,
        16: types.AdapterSize.ADAPTER_SIZE_SIXTEEN,
    }
    return types.CreateTuningJobConfig(
        tuned_model_display_name="thepower-soporte-s8",
        epoch_count=spec["epochs"],
        adapter_size=sizes[spec["adapter_size"]],
        validation_dataset=types.TuningDataset(gcs_uri=spec["validation_uri"]),
    )


# Despacha la acción CLI: la preparación es offline; subir/crear/estado usan Google.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # accion (posicional): preparar (offline), subir-datos (escribe en Cloud Storage),
    # crear (lanza el tuning y consume presupuesto) o estado (consulta un trabajo existente).
    p.add_argument("accion", choices=("preparar", "subir-datos", "crear", "estado"))
    # --proyecto: ID del proyecto Google Cloud del laboratorio; sin él se usa GOOGLE_CLOUD_PROJECT.
    p.add_argument("--proyecto")
    # --bucket: bucket de Cloud Storage para los JSONL; sin él se usa TUNING_BUCKET.
    p.add_argument("--bucket")
    # --job: nombre completo del trabajo de tuning que consulta la acción estado.
    p.add_argument("--job")
    # --presupuesto-usd y --coste-estimado-usd: obligatorios para subir-datos y crear;
    # solo se comparan aquí, Google no recibe ningún límite de gasto.
    p.add_argument("--presupuesto-usd", type=float)
    # type=float convierte el texto de la terminal en número (dólares).
    p.add_argument("--coste-estimado-usd", type=float)
    # Argumentos de la terminal convertidos a atributos como args.accion o args.proyecto.
    args = p.parse_args()
    # Carga .env antes de leer GOOGLE_CLOUD_PROJECT y TUNING_BUCKET.
    load_config()
    # Manifiesto verificado: datos, prompt y modelo siguen siendo los del experimento congelado.
    frozen = assert_frozen()
    # Proyecto explícito del laboratorio que recibirá la llamada Google.
    project = args.proyecto or os.getenv("GOOGLE_CLOUD_PROJECT")
    # Exige proyecto explícito antes de consultar/subir/crear; evita usar por accidente otro proyecto ADC.
    if not project:
        # Termina con un mensaje de uso; no se usa ningún proyecto por defecto.
        p.error(
            "Indica el proyecto del curso; no se toma un proyecto personal por defecto"
        )
    # Hace que las funciones compartidas utilicen el proyecto ya validado en esta ejecución.
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    # estado: solo consulta un trabajo existente; no necesita bucket ni presupuesto.
    if args.accion == "estado":
        # Para consultar estado exige el ID del trabajo existente; no crea otro entrenamiento.
        if not args.job:
            # Termina: sin nombre de trabajo no hay nada que consultar.
            p.error("--job es obligatorio")
        # Cliente Vertex AI en la región donde se creó el trabajo de tuning.
        client = google_client("europe-west4")
        # try/finally: el cliente se cierra aunque la consulta falle.
        try:
            # Consulta el trabajo por su nombre e imprime su estado como JSON; no crea otro.
            print(client.tunings.get(name=args.job).model_dump_json(indent=2))
        # Cierra el cliente aunque la consulta falle.
        finally:
            # Libera las conexiones del cliente.
            client.close()
        # Fin de la acción estado.
        return
    # Especificación del trabajo de tuning; describirla no equivale a ejecutarlo.
    spec = job_spec(project, args.bucket or os.getenv("TUNING_BUCKET"))
    # preparar: muestra especificación y manifiesto sin llamar a Google.
    if args.accion == "preparar":
        # JSON legible con la especificación; nada sale del equipo.
        print(
            json.dumps(
                {
                    # Especificación del trabajo.
                    "spec": spec,
                    # Valida también los tipos del SDK sin construir cliente ni llamar a Google.
                    "config_sdk": tuning_config(spec).model_dump(
                        mode="json", exclude_none=True
                    ),
                    # Manifiesto del experimento congelado.
                    "experimento": frozen,
                    # Recordatorio: preparar no llama a Google.
                    "estado": "PREPARADO; no se ha llamado a Google",
                },
                indent=2,
            )
        )
        # Fin de la acción preparar.
        return
    # Exige estimación y presupuesto como argumentos antes de una acción que consume/escribe recursos.
    if args.presupuesto_usd is None or args.coste_estimado_usd is None:
        # El parser detiene el comando e informa del argumento obligatorio o inválido.
        p.error(
            "Indica presupuesto autorizado y estimación previa; esto no crea un límite de gasto en Google"
        )
    # Rechaza una estimación superior al presupuesto o un presupuesto no positivo.
    if (
        not 0 <= args.coste_estimado_usd <= args.presupuesto_usd
        or args.presupuesto_usd <= 0
    ):
        # El parser detiene el comando e informa del argumento obligatorio o inválido.
        p.error("Estimación fuera del presupuesto")
    # subir-datos: copia a Cloud Storage los JSONL convertidos de train y validación.
    if args.accion == "subir-datos":
        # Cliente de Cloud Storage; solo se importa para esta acción.
        from google.cloud import storage

        # Cliente de Cloud Storage del proyecto del laboratorio; usa las credenciales ADC.
        client = storage.Client(project=project)
        # try/finally: el cliente se cierra aunque la subida falle.
        try:
            # Obtiene una referencia al bucket indicado; no crea un bucket nuevo.
            bucket = client.bucket(spec["train_uri"].split("/")[2])
            # Solo sube train y validación; el test se conserva aparte para la evaluación posterior.
            for split in ("train", "validacion"):
                # Escribe el JSONL en Cloud Storage; if_generation_match=0 rechaza sobrescribir un objeto previo.
                bucket.blob(f"thepower-s7-s8/{split}.jsonl").upload_from_filename(
                    ROOT / f"datos/gemini/{split}.jsonl",
                    content_type="application/jsonl",
                    if_generation_match=0,
                )
        # Cierra el cliente aunque la subida falle.
        finally:
            # Libera las conexiones del cliente.
            client.close()
        # Confirma qué se subió y recuerda que test queda fuera.
        print("Subidos train y validación; test no se ha subido")
    # crear: lanza el trabajo de tuning gestionado en Vertex AI; consume presupuesto.
    else:
        # Tipos del SDK para describir datasets y configuración del tuning.
        from google.genai import types

        # Cliente Vertex AI en la región del tuning (europe-west4).
        client = google_client(spec["location"])
        # try/finally: el cliente se cierra aunque la creación falle.
        try:
            # Trabajo de tuning creado en Google; su identificador permite consultar el mismo entrenamiento.
            job = client.tunings.tune(
                # Modelo base de la especificación.
                base_model=spec["base_model"],
                # JSONL de train en Cloud Storage.
                training_dataset=types.TuningDataset(gcs_uri=spec["train_uri"]),
                # Configuración validada por el SDK: nombre, épocas, tamaño 8 y validación.
                config=tuning_config(spec),
            )
            # Carpeta local de recibos del tuning; resultados/ está fuera de Git.
            path = ROOT / "resultados/google-tuning"
            # Crea la carpeta si falta (también resultados/).
            path.mkdir(parents=True, exist_ok=True)
            # Guarda la respuesta del trabajo con la fecha UTC en el nombre del archivo.
            (
                path / f"job-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
            ).write_text(job.model_dump_json(indent=2), encoding="utf-8")
            # Muestra nombre y estado del trabajo; el nombre se usa después con la acción estado.
            print(
                json.dumps(
                    {
                        # Nombre completo del trabajo; se pasa a --job en la acción estado.
                        "job": job.name,
                        # Estado inicial que informa Google.
                        "state": str(job.state),
                        # Presupuesto anotado al crear el trabajo.
                        "presupuesto_usd": args.presupuesto_usd,
                        "advertencia": "El presupuesto anotado no es un tope técnico del proveedor",
                    }
                )
            )
        # Cierra el cliente aunque la creación falle.
        finally:
            # Libera las conexiones del cliente.
            client.close()


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
