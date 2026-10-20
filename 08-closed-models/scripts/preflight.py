# GUÍA DE LECTURA · scripts/preflight.py
# Comprueba datos, hashes, dependencias y presencia del adaptador antes de clase.
# Informa si hay configuración, pero nunca imprime claves ni hace inferencia.
# Sin --local no consulta servidores; con --local solo lee el catálogo de modelos.
# Un preflight correcto no demuestra que un proveedor remoto o el entrenamiento funcionen.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
# Permite leer opciones de la terminal y generar ayuda del comando.
# Comprueba si un paquete está disponible sin cargar el modelo ni llamar al proveedor.
# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
# Lee configuración del entorno y ajusta opciones del proceso.
# Identifica versión de Python y entorno de ejecución para el registro.
import argparse
import importlib.util
import json
import os
import platform

import _bootstrap  # noqa: F401

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, assert_frozen, validate_splits

# Lectura acotada del catálogo de LM Studio cuando se usa --local.
from curso.http import bounded_json, model_ids

# Lectura de .env y ruta remota configurada, sin llamar al proveedor.
from curso.remote import (
    CREDENCIALES,
    configured_model,
    configured_provider,
    load_config,
)


# Lee --local, reúne comprobaciones y muestra un informe sin valores secretos.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # --local: consulta además el catálogo de modelos de LM Studio (solo lectura).
    p.add_argument("--local", action="store_true")
    # Argumentos de la terminal convertidos a atributos como args.local.
    args = p.parse_args()
    # Carga .env antes de comprobar qué variables existen; no imprime sus valores.
    load_config()
    # Reúne versión, integridad, paquetes y presencia de configuración; solo publica booleanos de credenciales.
    result = {
        # Versión de Python que ejecuta el script (el curso usa 3.12).
        "python": platform.python_version(),
        # Cantidades de train/validación/test tras validar las particiones.
        "splits": validate_splits(),
        # True si los hashes coinciden con el manifiesto congelado.
        "experimento_congelado": bool(assert_frozen()),
        # True/False por paquete: si está instalado en este entorno (sin importarlo).
        "dependencias": {
            m: importlib.util.find_spec(m) is not None
            for m in (
                "requests",
                "anthropic",
                "transformers",
                "torch",
                "trl",
                "peft",
                "datasets",
                "google.genai",
            )
        },
        # Ruta de LLM_PROVIDER/LLM_MODEL que usarán demo y evaluación remota sin --proveedor.
        "ruta_remota": {
            "proveedor": configured_provider(),
            "modelo": configured_model(),
        },
        # Presencia de credenciales por proveedor: solo booleanos, nunca valores.
        # Usa la misma tabla que require_credentials: basta con una variable de cada ruta.
        # Google se informa aparte, en google_proyecto_curso_configurado.
        "credenciales": {
            name: any(bool(os.getenv(var)) for var in variables)
            for name, variables in CREDENCIALES.items()
            if name != "google"
        },
        # True si hay proyecto de Google Cloud configurado (sin mostrarlo).
        "google_proyecto_curso_configurado": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        # True si ya existe un adaptador entrenado en la carpeta por defecto.
        "adaptador_local": (
            ROOT / "modelos/lora-soporte/adapter_model.safetensors"
        ).exists(),
        # Recordatorio: todos los datos del curso son ficticios.
        "datos_sinteticos": True,
        # preflight nunca llama a un modelo: la conexión remota queda sin probar.
        "conexion_remota": "No probada; preflight no consume inferencia",
    }
    # --local añade una lectura de catálogo HTTP; sin esta opción el preflight no consulta LM Studio.
    if args.local:
        # Cliente HTTP; las peticiones se realizan al llamarlo, no por el simple import.
        import requests

        # URL base del servidor local; LM Studio usa el puerto 1234 por defecto.
        base = os.getenv("LOCAL_BASE_URL") or "http://localhost:1234/v1"
        # Catálogo /models: lista los modelos cargados sin generar nada.
        url = base.rstrip("/") + "/models"
        # try/except: un fallo de red o de formato se informa como texto, sin detener el informe.
        try:
            # Respuesta HTTP que se inspeccionará y cerrará después de leerla.
            response = requests.get(url, timeout=5, stream=True, allow_redirects=False)
            # try/finally: la respuesta se cierra pase lo que pase.
            try:
                # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
                if response.status_code != 200:
                    # Detiene la lectura; el except de abajo lo convierte en un aviso.
                    raise ValueError("Catálogo HTTP no disponible")
                # Añade IDs de modelos válidos al informe; limita a diez segundos el recorrido de bloques.
                result["modelos_locales"] = model_ids(
                    bounded_json(response, max_seconds=10)
                )
            # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
            finally:
                # Libera la conexión.
                response.close()
        # Representa fallo HTTP/JSON como disponibilidad desconocida, sin imprimir cuerpos o claves.
        except (requests.RequestException, ValueError):
            # Texto de aviso en lugar de la lista de modelos.
            result["modelos_locales"] = (
                "Servidor local no disponible o respuesta inválida"
            )
    # Informe JSON en la terminal: credenciales como booleanos, nunca sus valores.
    print(json.dumps(result, ensure_ascii=False, indent=2))


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
