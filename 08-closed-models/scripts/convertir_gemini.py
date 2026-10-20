# GUÍA DE LECTURA · scripts/convertir_gemini.py
# Convierte las mismas particiones de S7 al JSONL requerido por Google.
# Conserva incidencia y respuesta objetivo y registra los IDs en un archivo aparte.
# Convertir datos no los sube a Google ni inicia un entrenamiento.
# Test se convierte para evaluar después, separado de train y validación.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import json

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, read_jsonl, write_jsonl, assert_frozen, digest

# Convierte una fila S7 al formato systemInstruction + contents de Gemini.
from curso.remote import gemini_record


# Escribe el JSONL convertido de cada partición y su correspondencia de IDs.
def main():
    # Comprueba integridad antes de convertir.
    assert_frozen()
    # Por partición: IDs en el orden de las líneas convertidas y hash del archivo.
    mapping = {}
    # Convierte cada partición por separado; ninguna línea de test entra en train.
    for split in ("train", "validacion", "test"):
        # Filas originales de la partición, en el mismo orden que tendrá el archivo convertido.
        rows = read_jsonl(ROOT / f"datos/{split}.jsonl")
        # Archivo de salida en datos/gemini/, uno por partición.
        path = ROOT / f"datos/gemini/{split}.jsonl"
        # Escribe un registro Gemini por fila y reemplaza la conversión anterior de esa partición.
        write_jsonl(path, [gemini_record(row) for row in rows])
        # Relaciona orden de líneas con IDs originales y calcula el hash del archivo convertido.
        mapping[split] = {
            "ids_por_linea": [r["id"] for r in rows],
            "sha256": digest(path),
        }
    # ids.json relaciona cada línea con su ID original y guarda el hash de cada archivo.
    (ROOT / "datos/gemini/ids.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    # Aviso en la terminal: la conversión es local y no sube nada a Google.
    print(
        "JSONL convertido; test separado de los archivos de entrenamiento y validación"
    )


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
