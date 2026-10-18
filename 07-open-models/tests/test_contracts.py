# GUÍA DE LECTURA · tests/test_contracts.py
# Pruebas del protocolo docente: particiones, few-shot, JSON y aislamiento.
# Usan datos sintéticos, directorios temporales y mocks, sin entrenar modelos.
# Cada test describe una propiedad que debe mantenerse al modificar el proyecto.

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
# Gestiona rutas de importación y el intérprete actual de Python.
# Crea directorios temporales de prueba que se retiran al salir del contexto.
# Organiza pruebas y aserciones; los tests se ejecutan solo al invocarlos.
import json, sys, tempfile, unittest

# Buffer de texto en memoria donde se descarta la ayuda que argparse escribe en stderr.
import io

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Añade una ruta de importación para poder reutilizar el paquete curso y los scripts del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# Funciones del núcleo compartido que se ponen a prueba.
from curso.common import (
    ROOT,
    assert_frozen,
    read_jsonl,
    validate_answer,
    validate_splits,
    messages,
    write_jsonl,
)

# Conversión al formato Gemini y cliente de Google Cloud.
from curso.remote import gemini_record, google_client

# Especificación offline del tuning de Gemini.
from gemini_tuning import job_spec, tuning_config

# Cálculo del resumen por condición.
from resumir import summarize

# Mocks sustituyen red/configuración para probar contratos sin proveedores reales.
from unittest.mock import patch

# Comprobación de la carpeta de salida del entrenamiento.
from entrenar_lora import training_output

# Funciones main de los scripts: se ejecutan con argumentos simulados en sys.argv.
from demo import main as demo_main

# main de evaluar_qwen.py.
from evaluar_qwen import main as evaluar_qwen_main

# main de publicar_adaptador.py.
from publicar_adaptador import main as publish_main


# Agrupa contratos del dataset, mensajes, validación y archivos del experimento.
class Contracts(unittest.TestCase):
    # Prepara una respuesta objetivo ficticia antes de cada prueba; no genera datos remotos.
    def setUp(self):
        # Objetivo ficticio con las tres claves del esquema.
        self.expected = {
            "categoria": "acceso",
            "prioridad": "media",
            "respuesta": "No compartas contraseñas.",
        }

    # Rechaza Markdown alrededor del JSON y valores no estándar como NaN.
    def test_json_strict_no_fences(self):
        # Un JSON rodeado de ```json … ``` (Markdown) no cuenta como JSON válido.
        self.assertFalse(
            validate_answer(
                "```json\n" + json.dumps(self.expected) + "\n```", self.expected
            )["json_valido"]
        )
        # NaN no existe en el JSON estándar: se rechaza.
        self.assertFalse(
            validate_answer('{"categoria":NaN}', self.expected)["json_valido"]
        )

    # Acepta el esquema correcto y rechaza claves adicionales.
    def test_exact_fields_and_enum(self):
        # El objetivo exacto cumple el esquema.
        self.assertTrue(
            validate_answer(json.dumps(self.expected), self.expected)["esquema_valido"]
        )
        # Copia del objetivo con una clave adicional.
        wrong = {**self.expected, "otra": 1}
        # Una clave adicional («otra») rompe el esquema.
        self.assertFalse(
            validate_answer(json.dumps(wrong), self.expected)["esquema_valido"]
        )

    # Comprueba que un fallo cuenta como caso y que coste desconocido sigue siendo None.
    def test_unparseable_is_in_denominator(self):
        # Dos casos simulados: uno correcto y otro con error y respuesta no parseable.
        rows = [
            {
                "valoracion": validate_answer(json.dumps(self.expected), self.expected),
                "latencia_s": 1,
                "coste_usd": None,
            },
            {
                "valoracion": validate_answer("error", self.expected),
                "latencia_s": None,
                "coste_usd": None,
                "error": "TimeoutError",
            },
        ]
        # Resumen calculado igual que en scripts/resumir.py.
        out = summarize(rows)
        # Los dos casos cuentan; solo uno acierta la categoría.
        self.assertEqual((out["casos"], out["categoria_correcta"]), (2, 1))
        # Coste desconocido en los casos: el total sigue siendo None, no 0.
        self.assertIsNone(out["coste_usd"])

    # Verifica las cantidades y los hashes del experimento publicado.
    def test_splits_and_freeze(self):
        # Cantidades publicadas: 240/30/30.
        self.assertEqual(
            validate_splits(), {"train": 240, "validacion": 30, "test": 30}
        )
        # Los hashes actuales coinciden con config/experimento-congelado.json.
        self.assertTrue(assert_frozen())

    # Introduce una familia de train en una copia temporal de test y exige rechazo.
    def test_duplicate_family_is_rejected(self):
        # Carpeta temporal: los datos reales del curso no se modifican.
        with tempfile.TemporaryDirectory() as tmp:
            # Recorre las tres particiones.
            for s in ("train", "validacion", "test"):
                # Copia de cada partición real.
                rows = read_jsonl(ROOT / f"datos/{s}.jsonl")
                # Solo en la copia de test se introduce una familia de train.
                if s == "test":
                    # Primer caso de test con la familia del primer grupo de train.
                    rows[0]["familia"] = "train-acceso-00"
                # Escribe la copia (modificada en el caso de test) en la carpeta temporal.
                write_jsonl(Path(tmp) / f"{s}.jsonl", rows)
            # La validación debe detectar la familia compartida y fallar.
            with self.assertRaisesRegex(ValueError, "Familia"):
                # Valida la carpeta temporal, no la real.
                validate_splits(tmp)

    # Comprueba que los ejemplos few-shot vienen de train y la consulta nueva queda al final.
    def test_fewshot_only_from_training(self):
        # Conversación few-shot para una consulta inventada.
        msg = messages("CONSULTA NUEVA", True)
        # La consulta nueva es el último mensaje.
        self.assertEqual(msg[-1]["content"], "CONSULTA NUEVA")
        # System + 4 pares user/assistant + consulta = 10 mensajes.
        self.assertEqual(len(msg), 10)
        # Todas las incidencias de train, para comprobar el origen de los ejemplos.
        training = {r["incidencia"] for r in read_jsonl(ROOT / "datos/train.jsonl")}
        # Todas las incidencias de ejemplo (turnos user intermedios) proceden de train.
        self.assertTrue(
            all(m["content"] in training for m in msg[1:-1] if m["role"] == "user")
        )

    # Comprueba que convertir formato conserva la incidencia y la respuesta objetivo.
    def test_gemini_conversion_preserves_labels(self):
        # Primer caso de test y su versión convertida al formato Gemini.
        row = read_jsonl(ROOT / "datos/test.jsonl")[0]
        # Registro con systemInstruction y contents.
        record = gemini_record(row)
        # El turno user conserva la incidencia original.
        self.assertEqual(record["contents"][0]["parts"][0]["text"], row["incidencia"])
        # El turno model conserva la respuesta objetivo exacta.
        self.assertEqual(
            json.loads(record["contents"][1]["parts"][0]["text"]), row["objetivo"]
        )
        # El ID no viaja en el registro convertido.
        self.assertNotIn("id", record)

    # Relaciona cada línea convertida con el ID de su ejemplo original.
    def test_gemini_id_mapping(self):
        # Correspondencia entre líneas e IDs guardada por convertir_gemini.py.
        ids = json.loads((ROOT / "datos/gemini/ids.json").read_text(encoding="utf-8"))
        # Compara cada partición.
        for s in ("train", "validacion", "test"):
            # El orden de IDs coincide con el de cada partición original.
            self.assertEqual(
                ids[s]["ids_por_linea"],
                [r["id"] for r in read_jsonl(ROOT / f"datos/{s}.jsonl")],
            )

    # Exige detenerse antes de crear cliente Google cuando falta el proyecto explícito.
    def test_missing_project_prevents_client(self):
        # Entorno vacío y load_config simulado: no se lee el .env real.
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("curso.remote.load_config"),
        ):
            # Sin GOOGLE_CLOUD_PROJECT debe fallar con un mensaje que menciona el laboratorio.
            with self.assertRaisesRegex(ValueError, "laboratorio"):
                # Debe fallar antes de crear el cliente.
                google_client()

    # Comprueba ubicación y ausencia del test en la especificación de tuning.
    def test_job_spec_never_includes_test(self):
        # Especificación del trabajo de tuning; describirla no equivale a ejecutarlo.
        spec = job_spec("curso-demo", "bucket-demo")
        # Ninguna ruta de la especificación menciona test.
        self.assertNotIn("test", json.dumps(spec))
        # El tuning se crea en europe-west4.
        self.assertEqual(spec["location"], "europe-west4")
        # Sin proyecto, la especificación no se construye.
        with self.assertRaises(ValueError):
            # Proyecto ausente.
            job_spec(None, "bucket")

    # El SDK instalado exige un enum para adapter_size; un entero hacía fallar crear.
    def test_tuning_config_uses_sdk_adapter_enum(self):
        from google.genai import types

        spec = job_spec("curso-demo", "bucket-demo")
        config = tuning_config(spec)
        self.assertEqual(config.adapter_size, types.AdapterSize.ADAPTER_SIZE_EIGHT)
        self.assertEqual(config.epoch_count, 2)
        self.assertEqual(config.validation_dataset.gcs_uri, spec["validation_uri"])
        self.assertNotIn("test.jsonl", config.model_dump_json())

    # Falla si importar el módulo intentara enviar una petición HTTP.
    def test_imports_do_not_connect(self):
        # importlib permite volver a ejecutar la importación de un módulo.
        import importlib

        # Si importar intentara enviar una petición, este requests.post simulado fallaría.
        with patch("requests.post", side_effect=AssertionError("network")):
            # Vuelve a importar curso.remote con la red bloqueada.
            importlib.reload(sys.modules["curso.remote"])

    # Prueba que una salida vacía se acepta y un adaptador previo permanece intacto.
    def test_training_does_not_overwrite_existing_artifacts(self):
        # Carpeta temporal: los adaptadores reales no se tocan.
        with tempfile.TemporaryDirectory() as tmp:
            # Carpeta de adaptador vacía dentro del directorio temporal.
            path = Path(tmp) / "adapter"
            # Crea la carpeta vacía.
            path.mkdir()
            # Una carpeta vacía es una salida válida.
            self.assertEqual(training_output(path), path.resolve())
            # Simula un adaptador ya entrenado dentro de la carpeta.
            artifact = path / "adapter_model.safetensors"
            # Contenido conocido para comprobar después que no cambió.
            artifact.write_bytes(b"preserve")
            # Con contenido dentro, se rechaza.
            with self.assertRaisesRegex(ValueError, "Salida no vacía"):
                # Segundo intento sobre la misma carpeta.
                training_output(path)
            # El archivo previo sigue intacto.
            self.assertEqual(artifact.read_bytes(), b"preserve")

    # write_jsonl escribe UTF-8 con saltos de línea LF en cualquier sistema operativo.
    def test_jsonl_is_utf8_with_lf(self):
        # Carpeta temporal: no toca los datos reales del curso.
        with tempfile.TemporaryDirectory() as tmp:
            # Archivo de prueba con dos registros que contienen tildes y eñes.
            path = Path(tmp) / "filas.jsonl"
            # Escribe los dos registros.
            write_jsonl(path, [{"texto": "contraseña"}, {"texto": "matrícula"}])
            # Bytes exactos del archivo, tal como se calcularía su hash.
            data = path.read_bytes()
            # La eñe se guarda en UTF-8 y no aparece ningún retorno de carro (\r) de Windows.
            self.assertIn("contraseña".encode("utf-8"), data)
            # \r no aparece: los saltos de línea son LF también en Windows.
            self.assertNotIn(b"\r", data)
            # Leer el archivo devuelve exactamente el texto escrito.
            self.assertEqual(read_jsonl(path)[1]["texto"], "matrícula")

    # demo.py termina con un mensaje de ayuda ante un caso inexistente, un --adaptador
    # fuera de Qwen o una --salida que ya existe, sin llegar a consultar ningún modelo.
    def test_demo_rejects_bad_arguments_before_calling_a_model(self):
        # Carpeta temporal con un resultado anterior que no debe sobrescribirse.
        with tempfile.TemporaryDirectory() as tmp:
            # Archivo que simula un resultado anterior.
            previous = Path(tmp) / "anterior.json"
            # Contenido conocido para comprobar después que no cambió.
            previous.write_text("{}", encoding="utf-8")
            # Tres líneas de comando incorrectas, como las escribiría un alumno en la terminal.
            for argv in (
                ["demo", "--proveedor", "qwen", "--caso", "DE-99"],
                ["demo", "--proveedor", "anthropic", "--adaptador", "modelos/otro"],
                ["demo", "--proveedor", "anthropic", "--salida", str(previous)],
            ):
                # argparse llama a sys.exit (SystemExit) y escribe la ayuda en stderr, que aquí se descarta.
                with (
                    patch("sys.argv", argv),
                    patch("curso.remote.chat") as call,
                    patch("sys.stderr", io.StringIO()),
                    self.assertRaises(SystemExit),
                ):
                    # Ejecuta main() con esos argumentos.
                    demo_main()
                # Ninguna consulta llegó al proveedor.
                call.assert_not_called()
            # El resultado anterior sigue intacto.
            self.assertEqual(previous.read_text(encoding="utf-8"), "{}")

    # qwen_lora sin adaptador entrenado se detiene antes de cargar Qwen y sin crear resultados.
    def test_lora_evaluation_requires_trained_adapter(self):
        # Carpeta temporal donde el adaptador no existe.
        with tempfile.TemporaryDirectory() as tmp:
            # Ruta del archivo de resultados que no debe llegar a crearse.
            output = Path(tmp) / "qwen_lora.jsonl"
            # Argumentos con una carpeta de adaptador inexistente.
            argv = [
                "evaluar_qwen",
                "--condicion",
                "qwen_lora",
                "--adaptador",
                str(Path(tmp) / "falta"),
                "--salida",
                str(output),
            ]
            # load_qwen simulado: si se llamara, la prueba lo detectaría.
            with (
                patch("sys.argv", argv),
                patch("curso.qwen.load_qwen") as load,
                patch("sys.stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                # Ejecuta main() con esos argumentos.
                evaluar_qwen_main()
            # No se cargó el modelo ni se escribió el archivo de resultados.
            load.assert_not_called()
            # El archivo de resultados no se creó.
            self.assertFalse(output.exists())

    # Publicar comprueba el adaptador local antes de crear nada en Hugging Face.
    def test_publish_checks_adapter_before_creating_repo(self):
        # Carpeta temporal vacía: le faltan adapter_config.json y adapter_model.safetensors.
        with tempfile.TemporaryDirectory() as tmp:
            # HfApi simulado: si se creara el cliente del Hub, la prueba lo detectaría.
            with (
                patch(
                    "sys.argv",
                    ["publicar", "--repo", "usuario/nuevo", "--adaptador", tmp],
                ),
                patch("huggingface_hub.HfApi") as api,
                patch("sys.stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                # Ejecuta main() con esos argumentos.
                publish_main()
            # No se llegó a crear el cliente, así que tampoco ningún repositorio.
            api.assert_not_called()


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Ejecuta las pruebas de este archivo.
    unittest.main()
