# GUÍA DE LECTURA · scripts/resumir.py
# Convierte lotes completos en evidencia JSON, CSV y una tabla Markdown.
# Todos los casos permanecen en el denominador, incluidos errores e inválidos.
# Antes de combinar, comprueba IDs, partición, tamaño y manifiesto del experimento.
# El CSV neutraliza fórmulas; el JSON conserva exactamente el texto original.

# Hace visible la raíz del proyecto al ejecutar un archivo desde scripts/.
import _bootstrap  # noqa: F401

# Permite leer opciones de la terminal y generar ayuda del comando.
# Escribe/lee tablas CSV con comillas y separadores correctos.
# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
# Calcula medianas de tiempos conocidos sin convertir ausencias en cero.
import argparse, csv, json, statistics

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Reutiliza funciones del núcleo compartido para mantener el mismo protocolo entre scripts.
from curso.common import ROOT, read_jsonl


# Seis condiciones del ejercicio; las adicionales se informan aparte.
CONDITIONS = (
    "qwen_base",
    "qwen_fewshot",
    "qwen_lora",
    "gemini_base",
    "gemini_ajustado",
    "claude_prompt",
)
# Condiciones adicionales: cualquier proveedor con el prompt básico y la demo histórica de Gemini.
EXTRA_CONDITIONS = ("remoto_basico", "gemini_openrouter_demo")


# Neutraliza texto que una hoja de cálculo podría interpretar como fórmula.
# Esta representación protege el CSV; la evidencia JSON se conserva sin alteración.
def csv_text(value):
    """La evidencia JSON permanece exacta; el CSV trata las fórmulas como texto."""
    # Detecta prefijos de fórmula y caracteres de control antes de escribir texto en CSV.
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        # Un apóstrofo inicial hace que la hoja de cálculo lo muestre como texto.
        return "'" + value
    # Números, None y texto normal se escriben sin cambios.
    return value


# Cuenta aciertos y errores, calcula mediana de tiempos conocidos y suma coste conocido.
# Si falta cualquier coste, devuelve None en lugar de inventar un total.
def summarize(rows):
    # Número total de casos del lote; los inválidos siguen en el denominador.
    n = len(rows)
    # Devuelve conteos y métricas disponibles; no convierte medidas desconocidas en cero.
    return {
        # Número de casos evaluados (30 en un lote completo).
        "casos": n,
        # Modelo y ruta realmente usados: el nombre de la condición no basta para saberlo.
        "modelos": sorted({r["model"] for r in rows if r.get("model")}),
        # Rutas usadas (anthropic, openrouter…); las condiciones Qwen no tienen ruta.
        "rutas": sorted({r["ruta"] for r in rows if r.get("ruta")}),
        # Cuántos casos cumplen cada bandera del validador (True suma 1).
        **{
            key: sum(bool(r["valoracion"][key]) for r in rows)
            for key in (
                "json_valido",
                "esquema_valido",
                "categoria_correcta",
                "prioridad_correcta",
                "ambas_correctas",
            )
        },
        # Casos con excepción registrada.
        "errores": sum(bool(r.get("error")) for r in rows),
        # Mediana solo de los tiempos conocidos; si no hay ninguno, None.
        "latencia_mediana_s": statistics.median(
            r["latencia_s"] for r in rows if r.get("latencia_s") is not None
        )
        if any(r.get("latencia_s") is not None for r in rows)
        else None,
        # Suma solo si se conoce el coste de todos los casos; uno desconocido deja None.
        "coste_usd": sum(r["coste_usd"] for r in rows)
        if rows and all(r.get("coste_usd") is not None for r in rows)
        else None,
    }


# Verifica lotes comparables y escribe registros JSON, resumen, CSV y tabla Markdown.
def main():
    # Parser de argumentos: describe las opciones que admite este comando.
    p = argparse.ArgumentParser()
    # --carpeta: donde están los JSONL de cada condición (qwen_base.jsonl, claude_prompt.jsonl…).
    p.add_argument("--carpeta", default=str(ROOT / "resultados"))
    # --destino: carpeta del informe (resultados.json, resumen.json, resultados.csv, comparacion.md).
    p.add_argument("--destino", default=str(ROOT / "material/evidencias"))
    # Argumentos de la terminal convertidos a atributos como args.carpeta o args.destino.
    args = p.parse_args()
    # Carpeta de lectura con un JSONL por condición.
    folder = Path(args.carpeta)
    # Carpeta de escritura del informe; se crea si falta.
    output = Path(args.destino)
    # parents=True crea carpetas intermedias; exist_ok=True no falla si ya existe.
    output.mkdir(parents=True, exist_ok=True)
    # Todos los registros originales de todas las condiciones, para resultados.json y el CSV.
    records = []
    # Resumen por condición; distingue resultados medidos y condiciones pendientes.
    report = {}
    # Procesa cada condición por separado para no mezclar sus casos y métricas.
    for cond in CONDITIONS + EXTRA_CONDITIONS:
        # Cada condición tiene su archivo, por ejemplo resultados/qwen_lora.jsonl.
        path = folder / f"{cond}.jsonl"
        # Casos de esa condición; lista vacía si todavía no se ha ejecutado.
        rows = read_jsonl(path) if path.exists() else []
        # Solo resume un lote si existe evidencia; las condiciones ausentes siguen pendientes.
        if rows:
            # Un caso evaluado dos veces contaría doble.
            if len({r["id"] for r in rows}) != len(rows):
                # Detiene el informe: hay que revisar o repetir ese lote.
                raise ValueError("IDs repetidos en evaluación")
            # Exige un lote completo de 30 casos; no presenta un subconjunto como el resultado final.
            if len(rows) != 30:
                # Detiene el informe e indica cuántos casos tiene el lote.
                raise ValueError(f"Lote incompleto {cond}: {len(rows)}")
            # La comparación final usa solo test: un caso de otra partición invalida el lote.
            if any(r["split"] != "test" for r in rows):
                # Detiene el informe: un lote de desarrollo no sirve para la comparación final.
                raise ValueError("Mezcla desarrollo y test")
            # Todos los casos del lote deben llevar el mismo manifiesto del experimento.
            if len({json.dumps(r["experimento"], sort_keys=True) for r in rows}) != 1:
                # Detiene el informe: el lote mezcla configuraciones.
                raise ValueError("Configuración cambió durante lote")
            # Calcula estadísticas de la condición y conserva también sus registros originales.
            report[cond] = summarize(rows)
            # Añade los registros de esta condición a la lista global.
            records += rows
        # Marca ausencia de ejecución explícitamente; cero casos no se presenta como cero errores.
        else:
            # Condición sin archivo: queda marcada como pendiente.
            report[cond] = {"casos": 0, "estado": "PENDIENTE; no hay ejecución"}
    # Compara manifiestos entre condiciones para impedir mezclar protocolos distintos en una tabla.
    manifests = {json.dumps(r["experimento"], sort_keys=True) for r in records}
    # Si dos condiciones usan manifiestos distintos, la tabla no sería comparable.
    if len(manifests) > 1:
        # Detiene el informe: no se mezclan protocolos distintos en una tabla.
        raise ValueError("Lotes con distintos datos/protocolo")
    # resultados.json: todos los registros con su respuesta original, sin reparar.
    (output / "resultados.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # resumen.json: métricas por condición, incluidas las pendientes.
    (output / "resumen.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Columnas del CSV, separando metadatos, respuesta original y banderas del validador.
    fields = [
        # Identificación del caso y de la condición.
        "id",
        "condicion",
        # Modelo, proveedor y ruta que respondieron.
        "model",
        "provider",
        "ruta",
        # Consumo: tiempo, tokens y coste (vacío si se desconoce).
        "latencia_s",
        "tokens_entrada",
        "tokens_salida",
        "coste_usd",
        # Excepción registrada, si la hubo.
        "error",
        # Texto original del modelo.
        "respuesta_original",
        # Banderas del validador.
        "json_valido",
        "esquema_valido",
        "categoria_correcta",
        "prioridad_correcta",
        "ambas_correctas",
    ]
    # El contexto abre el archivo y lo cierra automáticamente al terminar.
    with (output / "resultados.csv").open("w", newline="", encoding="utf-8") as f:
        # Crea columnas explícitas y escribe cabecera; CSV conserva claves de valoración y metadatos.
        writer = csv.DictWriter(f, fieldnames=fields)
        # Primera fila del CSV con los nombres de las columnas.
        writer.writeheader()
        # Escribe cada registro neutralizando fórmulas solo en la representación CSV.
        # Cada columna sale del registro o, para las banderas, de su campo valoracion.
        for row in records:
            # Una fila por caso evaluado.
            writer.writerow(
                {k: csv_text(row.get(k, row["valoracion"].get(k))) for k in fields}
            )
    # Líneas del informe Markdown que se guardará al finalizar.
    lines = [
        # Título del informe.
        "# Comparación S7/S8",
        "",
        # Nota sobre la muestra y el protocolo.
        "Muestra sintética de 30 casos por condición. Sin reparación ni reintentos correctores.",
        "",
        # Cabecera de la tabla.
        "| Condición | Modelo · ruta | Casos | JSON | Categoría | Prioridad | Ambas | Mediana s | Coste USD |",
        # Fila separadora; ---: alinea las cifras a la derecha.
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    # Procesa cada condición por separado; las adicionales solo aparecen si tienen resultados.
    for cond in CONDITIONS + EXTRA_CONDITIONS:
        # Recupera las estadísticas que se van a presentar en una fila de Markdown.
        r = report[cond]
        # Muestra pendiente y No disponible cuando no hay ejecución, y pasa a la siguiente condición.
        if not r["casos"]:
            # Las condiciones adicionales sin ejecución no se muestran.
            if cond in CONDITIONS:
                # Fila de condición pendiente, sin cifras.
                lines.append(
                    f"| {cond} | - | Pendiente | - | - | - | - | - | No disponible |"
                )
            # continue salta a la siguiente condición del bucle.
            continue
        # Modelo y ruta usados, para que la tabla diga qué se comparó de verdad.
        used = (
            " · ".join(
                part
                for part in (", ".join(r["modelos"]), ", ".join(r["rutas"]))
                if part
            )
            or "-"
        )
        # Función auxiliar de presentación: muestra desconocidos como No disponible en la tabla.
        fmt = lambda k: str(r[k]) if r[k] is not None else "No disponible"
        # Construye la fila visible con conteos, mediana y coste disponible de la condición.
        lines.append(
            "| "
            + " | ".join(
                # Primeras columnas: condición, modelo/ruta y número de casos.
                [cond, used, str(r["casos"])]
                # Resto de columnas: aciertos, mediana de latencia y coste.
                + [
                    fmt(k)
                    for k in (
                        "json_valido",
                        "categoria_correcta",
                        "prioridad_correcta",
                        "ambas_correctas",
                        "latencia_mediana_s",
                        "coste_usd",
                    )
                ]
            )
            # Cierre de la fila Markdown.
            + " |"
        )
    # Añade el límite docente: Gemini/OpenRouter no sustituye el par Google base/ajustado.
    lines += [
        "",
        "Las filas sin ejecución permanecen pendientes. remoto_basico y gemini_openrouter_demo",
        "son condiciones adicionales; no sustituyen la pareja Google base/ajustado.",
    ]
    # comparacion.md: tabla Markdown lista para la entrega.
    (output / "comparacion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Imprime el resumen por condición en la terminal.
    print(json.dumps(report))


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Invoca el punto de entrada únicamente cuando se ejecuta este archivo como programa.
    main()
