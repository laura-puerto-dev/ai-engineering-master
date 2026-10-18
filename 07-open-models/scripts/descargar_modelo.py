# GUÍA DE LECTURA · scripts/descargar_modelo.py
# Descarga a la caché de Hugging Face los archivos del checkpoint fijado.
# Necesita red si no están ya descargados; no entrena ni ejecuta una consulta.
# Se seleccionan pesos Safetensors y archivos auxiliares para Transformers.
# La revisión congelada evita comparar versiones distintas del modelo.

"""Descargar únicamente el checkpoint público fijado para la práctica local."""

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import json

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import MODEL_ID, REVISION, assert_frozen


# Verifica el protocolo y descarga únicamente los archivos permitidos de la revisión fijada.
def main():
    # Verifica que el modelo y los hashes siguen correspondiendo al protocolo fijado.
    assert_frozen()
    # snapshot_download descarga una revisión concreta de un repositorio del Hub a la caché local.
    from huggingface_hub import snapshot_download

    # Descarga a la caché la revisión exacta: solo configuración, pesos y tokenizer;
    # token=False no usa ninguna cuenta y max_workers=2 limita las descargas en paralelo.
    snapshot_download(
        repo_id=MODEL_ID,
        revision=REVISION,
        token=False,
        max_workers=2,
        allow_patterns=[
            "config.json",
            "generation_config.json",
            "*.safetensors",
            "*.safetensors.index.json",
            "tokenizer*",
            "vocab.json",
            "merges.txt",
            "added_tokens.json",
            "special_tokens_map.json",
            "chat_template.jinja",
        ],
    )
    # Confirma en la terminal qué modelo y revisión quedaron en la caché.
    print(json.dumps({"modelo": MODEL_ID, "revision": REVISION, "descargado": True}))


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
