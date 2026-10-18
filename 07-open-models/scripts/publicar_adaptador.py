# GUÍA DE LECTURA · scripts/publicar_adaptador.py
# Publica un adaptador local en un repositorio PRIVADO NUEVO del usuario autenticado.
# Sube solo los archivos permitidos y conserva el commit devuelto por el Hub.
# Descarga ese commit, recarga base + adaptador y hace una consulta de comprobación.
# Esta acción escribe en Hugging Face; no contrata un endpoint de inferencia.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Permite leer opciones de la terminal y generar ayuda del comando.
# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import argparse, json

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT


# Verifica usuario, crea repo privado nuevo, publica y prueba recarga por commit.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # --repo: usuario/nombre del repositorio privado NUEVO que se creará en Hugging Face.
    p.add_argument("--repo", required=True, help="usuario/repo privado del curso")
    # --adaptador: carpeta local del adaptador entrenado.
    p.add_argument("--adaptador", default=str(ROOT / "modelos/lora-soporte"))
    # Argumentos de la terminal convertidos a atributos como args.repo o args.adaptador.
    args = p.parse_args()
    # Exige un repo en formato usuario/nombre para identificar quién será su propietario.
    if "/" not in args.repo:
        # Termina con un mensaje de uso antes de contactar con el Hub.
        p.error("Indica usuario/repo")
    # Carpeta local del adaptador que se va a publicar.
    adapter = Path(args.adaptador)
    # Comprueba los archivos ANTES de crear el repositorio: un error no deja un repo vacío en el Hub.
    missing = [
        name
        for name in ("adapter_config.json", "adapter_model.safetensors")
        if not (adapter / name).exists()
    ]
    # Alguno de los dos archivos falta.
    if missing:
        # Termina con un mensaje de uso; no se ha creado nada en el Hub.
        p.error(
            f"Faltan {', '.join(missing)} en {adapter}; entrena primero el adaptador"
        )
    # HfApi crea repositorios y sube archivos; snapshot_download descarga un commit concreto.
    from huggingface_hub import HfApi, snapshot_download

    # Cliente del Hub; usa el token de Hugging Face guardado en este equipo y nunca lo muestra.
    api = HfApi()
    # whoami pregunta al Hub qué usuario corresponde a ese token.
    who = api.whoami()
    # Solo publica en tu propio usuario; publicar en una organización exige revisarlo a mano.
    if args.repo.split("/")[0] != who["name"]:
        # Termina antes de crear nada en el Hub.
        p.error(
            "Usa el usuario autenticado; organizaciones requieren revisión explícita"
        )
    # Crea un repo privado nuevo; exist_ok=False falla si ya existe y así nunca modifica uno anterior.
    api.create_repo(args.repo, private=True, exist_ok=False)
    # Sube en un único commit solo los archivos de allow_patterns y devuelve los datos de ese commit.
    receipt = api.upload_folder(
        # Repositorio recién creado.
        repo_id=args.repo,
        # Carpeta local del adaptador.
        folder_path=args.adaptador,
        # Solo estos archivos: pesos y configuración LoRA, ficha (README) y registro del entrenamiento.
        allow_patterns=[
            "adapter_config.json",
            "adapter_model.safetensors",
            "README.md",
            "entrenamiento.json",
        ],
        # Mensaje del commit, visible en el historial del repositorio.
        commit_message="Adaptador docente S7 con datos sintéticos",
    )
    # Commit exacto publicado que se recargará para comprobar el adaptador remoto.
    revision = receipt.oid
    # Descarga ese commit (solo configuración y pesos LoRA) y devuelve su carpeta en la caché local.
    local = snapshot_download(
        # Repositorio publicado.
        args.repo,
        # Commit exacto recién creado, no la última versión de la rama.
        revision=revision,
        # Solo lo necesario para recargar el adaptador.
        allow_patterns=["adapter_config.json", "adapter_model.safetensors"],
    )
    # Carga Qwen solo después de publicar: la comprobación usa los archivos bajados del Hub.
    from curso.qwen import load_qwen, generate

    # Recarga la base original con los archivos descargados del commit recién publicado.
    model, tok, device = load_qwen(local)
    # Consulta de comprobación con una incidencia fija (no de test): demuestra que el adaptador publicado funciona.
    result = generate(model, tok, device, "Tengo un cargo duplicado en mi matrícula.")
    # Evidencia local de la recarga en material/evidencias/, carpeta ignorada por Git.
    path = ROOT / "material/evidencias/huggingface-recarga.json"
    # Crea material/evidencias/ si falta; en una copia nueva del repo no existe.
    path.parent.mkdir(parents=True, exist_ok=True)
    # Guarda repo, commit y respuesta de la recarga como evidencia.
    path.write_text(
        json.dumps(
            {
                # Repositorio y commit publicados.
                "repo": args.repo,
                "revision": revision,
                # Se creó como privado.
                "private": True,
                # Respuesta de la consulta de comprobación, con tokens y tiempo.
                "recarga": result,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # Resumen en la terminal: repo, commit y privacidad; nunca el token.
    print(json.dumps({"repo": args.repo, "revision": revision, "private": True}))


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
