# GUÍA DE LECTURA · tests/test_output_security.py
# Pruebas de límites de respuestas y preservación de la evidencia.
# Mocks simulan proveedores; una prueba usa gzip servido en loopback.
# Se comprueban redirects, tamaño descomprimido, JSON, CSV y cierre de recursos.
# Ninguna prueba llama a un proveedor remoto ni imprime una clave real.

# Escribe/lee tablas CSV con comillas y separadores correctos.
import csv

# Comprime la respuesta ficticia para comprobar límites de bytes descomprimidos.
import gzip

# Buffers de memoria permiten inspeccionar salidas de pruebas sin escribir archivos reales.
import io

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import json

# Gestiona rutas de importación y el intérprete actual de Python.
import sys

# Crea directorios temporales de prueba que se retiran al salir del contexto.
import tempfile

# Organiza pruebas y aserciones; los tests se ejecutan solo al invocarlos.
import unittest

# Captura stdout en memoria para inspeccionar el informe generado dentro de una prueba.
from contextlib import redirect_stdout

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Mocks sustituyen red/configuración para probar contratos sin proveedores reales.
from unittest.mock import Mock, patch

# Añade una ruta de importación para poder reutilizar el paquete curso y los scripts del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# Funciones y constantes del núcleo compartido que se ponen a prueba.
from curso.common import (
    ROOT,
    MAX_MODEL_TEXT_CHARS,
    assert_frozen,
    read_jsonl,
    validate_answer,
    write_jsonl,
)

# Límite de transporte y lectores acotados de curso/http.py.
from curso.http import MAX_RESPONSE_BYTES, bounded_json, joined_text, model_ids

# Adaptadores de LM Studio, OpenRouter y Vertex AI, y la búsqueda en el catálogo de
# OpenRouter, cuya caché se vacía entre pruebas.
from curso.remote import chat_local, chat_openrouter, chat_google, openrouter_model

# Funciones de los scripts que se ejecutan dentro de las pruebas.
from resumir import csv_text, main as summarize_main

# main de preflight.py, para ejecutarlo con argumentos simulados.
from preflight import main as preflight_main

# main de evaluar_remotos.py, para ejecutar un lote simulado.
from evaluar_remotos import main as evaluate_main


# Fabrica una respuesta HTTP simulada con bloques, cabeceras y métodos observables.
# Permite comprobar límites y cierre sin acceder a un proveedor externo.
def response(data=None, chunks=None, headers=None, status=200):
    # Mock acepta cualquier llamada y registra cómo se usó; aquí simula una respuesta de requests.
    value = Mock(status_code=status, headers=headers or {})
    # iter_content devolverá estos bloques de bytes: los indicados o el JSON de data codificado.
    value.iter_content.return_value = (
        chunks if chunks is not None else [json.dumps(data).encode()]
    )
    # Respuesta simulada lista para pasarla al código del curso.
    return value


# Agrupa pruebas de transporte acotado y conservación de resultados originales.
class OutputSecurity(unittest.TestCase):
    # Prueba límites de cabecera, bytes descomprimidos, plazo y cierre en rutas de error.
    def test_http_header_and_decoded_chunks_are_bounded_and_closed(self):
        # Cabecera que anuncia un byte más del límite.
        oversized = response(headers={"Content-Length": str(MAX_RESPONSE_BYTES + 1)})
        # Debe fallar por tamaño sin leer el cuerpo.
        with self.assertRaisesRegex(ValueError, "bytes"):
            # Llamada que debe fallar.
            bounded_json(oversized)
        # No se llegó a leer ningún bloque.
        oversized.iter_content.assert_not_called()
        # La respuesta se cerró una vez.
        oversized.close.assert_called_once()
        # Sin cabecera y con una cabecera falsa de 2 bytes: el límite se aplica a los bytes reales.
        for headers in ({}, {"Content-Length": "2"}):
            # 129 bloques de 8 KiB: algo más de 1 MiB en total.
            chunks = response(chunks=[b"x" * 8192] * 129, headers=headers)
            # Debe fallar al superar 1 MiB acumulado.
            with self.assertRaisesRegex(ValueError, "bytes"):
                # Llamada que debe fallar.
                bounded_json(chunks)
            # La respuesta se cerró una vez.
            chunks.close.assert_called_once()
        # Respuesta pequeña y correcta.
        valid = response({"choices": []})
        # Una respuesta pequeña se lee completa.
        self.assertEqual(bounded_json(valid), {"choices": []})
        # También se cierra en el camino de éxito.
        valid.close.assert_called_once()

    # Sirve gzip por HTTP local y comprueba el límite sobre su tamaño descomprimido.
    def test_real_compressed_response_limit(self):
        # Servidor HTTP de la biblioteca estándar para servir gzip en loopback.
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        # Hilo en segundo plano para ejecutar el servidor de prueba.
        from threading import Thread

        # Cliente HTTP real para leer del servidor de prueba.
        import requests

        # Cuerpo comprimido con gzip que, al descomprimirse, supera el límite de 1 MiB.
        body = gzip.compress(
            json.dumps({"text": "x" * (MAX_RESPONSE_BYTES + 1)}).encode()
        )

        # Handler local de prueba que sirve una respuesta comprimida controlada.
        class Handler(BaseHTTPRequestHandler):
            # Sirve bytes gzip controlados para comprobar que el lector limita el tamaño descomprimido.
            def do_GET(self):
                # Estado 200 OK.
                self.send_response(200)
                # Indica que el cuerpo viene comprimido.
                self.send_header("Content-Encoding", "gzip")
                # Tamaño comprimido (pequeño): engañaría a quien solo mirase la cabecera.
                self.send_header("Content-Length", str(len(body)))
                # Fin de las cabeceras.
                self.end_headers()
                # Envía el cuerpo comprimido.
                self.wfile.write(body)

            # Silencia el log del servidor temporal para que la prueba solo muestre su resultado.
            def log_message(self, *args):
                # No escribe nada en la terminal.
                pass

        # Puerto 0: el sistema elige uno libre.
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # Hilo en segundo plano que atiende la petición.
        thread = Thread(target=server.serve_forever, daemon=True)
        # Arranca el servidor de prueba.
        thread.start()
        # try/finally: el servidor se detiene aunque la prueba falle.
        try:
            # requests descomprime gzip automáticamente al leer por bloques.
            result = requests.get(
                f"http://127.0.0.1:{server.server_port}/", stream=True, timeout=2
            )
            # El lector cuenta bytes descomprimidos y rechaza la respuesta.
            with self.assertRaisesRegex(ValueError, "bytes"):
                # Lectura acotada de la respuesta comprimida: debe fallar.
                bounded_json(result)
        finally:
            # Detiene el servidor de prueba.
            server.shutdown()
            # Libera el socket del servidor.
            server.server_close()
            # Espera a que termine su hilo.
            thread.join()

    # Rechaza catálogos mal formados y listas/bloques de respuesta demasiado grandes.
    def test_catalog_shape_and_part_limits(self):
        # Un catálogo correcto devuelve sus IDs en orden.
        self.assertEqual(
            model_ids({"data": [{"id": "one"}, {"id": "two"}]}), ["one", "two"]
        )
        # Catálogos inválidos:
        for entries in (
            # entrada sin id,
            [{}],
            # entrada que no es un objeto,
            [None],
            # id de más de 1024 caracteres,
            [{"id": "x" * 1025}],
            # más de 256 modelos
            [{"id": "one"}] * 257,
            # o data que no es una lista.
            "bad",
        ):
            # Cada catálogo inválido se rechaza; subTest identifica cuál falla.
            with (
                self.subTest(entries_type=type(entries).__name__),
                self.assertRaises(ValueError),
            ):
                # Llamada que debe fallar.
                model_ids({"data": entries})
        # Bloques correctos se unen en orden.
        self.assertEqual(
            joined_text([{"text": "uno"}, {"text": "dos"}], "text"), "unodos"
        )
        # Respuestas inválidas:
        for parts in (
            # más de 64 bloques,
            [{"text": "x"}] * 65,
            # más de 1 MiB en total
            [{"text": "x" * MAX_RESPONSE_BYTES}, {"text": "x"}],
            # o un texto que no es una cadena.
            [{"text": 1}],
        ):
            # Cada respuesta inválida se rechaza.
            with self.assertRaises(ValueError):
                # Llamada que debe fallar.
                joined_text(parts, "text")

    # Comprueba stream=True, ausencia de redirects y conservación del texto en los tres clientes.
    def test_all_http_clients_stream_and_preserve_normal_text(self):
        # Texto que devolverán los tres clientes simulados.
        raw = '{"categoria":"consulta","prioridad":"baja","respuesta":"Información."}'
        # Envoltorio de Chat Completions con ese texto.
        envelope = {"choices": [{"message": {"content": raw}}]}
        # LM Studio por la interfaz compatible (False) y por la API nativa (True).
        for native in (False, True):
            # Respuesta simulada con el formato de cada API de LM Studio.
            value = response(
                {"output": [{"type": "message", "content": raw}]}
                if native
                else envelope
            )
            # load_config simulado y requests.post sustituido: no hay red.
            with (
                patch("curso.remote.load_config"),
                patch("requests.post", return_value=value) as post,
            ):
                # El texto llega exactamente igual.
                self.assertEqual(
                    chat_local("incidencia", model="demo", native=native)[
                        "respuesta_original"
                    ],
                    raw,
                )
                # La petición se hizo con stream=True (lectura acotada).
                self.assertTrue(post.call_args.kwargs["stream"])
                # Y sin seguir redirecciones.
                self.assertFalse(post.call_args.kwargs["allow_redirects"])
        # Respuesta de OpenRouter con el mismo texto.
        value = response(envelope)
        # Catálogo simulado con la ficha mínima del modelo demo.
        listing = response({"data": [{"id": "demo"}]})
        # Vacía la caché del catálogo antes y después para no mezclar pruebas.
        openrouter_model.cache_clear()
        # addCleanup ejecuta la limpieza al terminar la prueba, aunque falle.
        self.addCleanup(openrouter_model.cache_clear)
        # Clave ficticia y red simulada (catálogo y consulta).
        with (
            patch("curso.remote.load_config"),
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy"}),
            patch("requests.get", return_value=listing),
            patch("requests.post", return_value=value) as post,
        ):
            # El texto llega exactamente igual.
            self.assertEqual(
                chat_openrouter("incidencia", "demo")["respuesta_original"], raw
            )
            # stream=True.
            self.assertTrue(post.call_args.kwargs["stream"])
            # Sin seguir redirecciones.
            self.assertFalse(post.call_args.kwargs["allow_redirects"])
        # Respuesta de Vertex AI con el mismo texto.
        value = response({"candidates": [{"content": {"parts": [{"text": raw}]}}]})
        # Sesión simulada: devuelve una respuesta controlada y permite verificar petición y cierre sin Google.
        session = Mock()
        # La sesión simulada devuelve esa respuesta al llamar a post.
        session.post.return_value = value
        # Proyecto ficticio, credenciales simuladas y sesión simulada.
        with (
            patch("curso.remote.load_config"),
            patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "demo"}),
            patch("google.auth.default", return_value=(Mock(), None)),
            patch(
                "google.auth.transport.requests.AuthorizedSession", return_value=session
            ),
        ):
            # El texto llega exactamente igual.
            self.assertEqual(
                chat_google("incidencia", "demo")["respuesta_original"], raw
            )
            # stream=True.
            self.assertTrue(session.post.call_args.kwargs["stream"])
            # Sin seguir redirecciones.
            self.assertFalse(session.post.call_args.kwargs["allow_redirects"])
            # La sesión se cerró una vez.
            session.close.assert_called_once()
        # Respuesta compatible con un texto un carácter más largo que el límite del validador.
        too_long = response(
            {"choices": [{"message": {"content": "x" * (MAX_MODEL_TEXT_CHARS + 1)}}]}
        )
        # load_config simulado y red simulada.
        with (
            patch("curso.remote.load_config"),
            patch("requests.post", return_value=too_long),
        ):
            # Respuesta local simulada de más de 16 KiB por la interfaz compatible.
            output = chat_local("incidencia", model="demo", native=False)
        # Se conserva el texto completo, sin recortar.
        self.assertEqual(output["respuesta_original"], "x" * (MAX_MODEL_TEXT_CHARS + 1))
        # Pero el validador no lo acepta como JSON válido.
        self.assertFalse(
            validate_answer(output["respuesta_original"], {})["json_valido"]
        )

    # Rechaza redirects antes de leer el cuerpo y respuestas Google sin candidatos.
    def test_redirects_fail_before_body_or_followup_and_google_no_candidates_fails(
        self,
    ):
        # Redirección 302 que además anuncia un cuerpo enorme.
        value = response(
            status=302,
            headers={
                "Location": "http://example.invalid",
                "Content-Length": str(MAX_RESPONSE_BYTES * 2),
            },
        )
        # load_config simulado y red simulada.
        with (
            patch("curso.remote.load_config"),
            patch("requests.post", return_value=value) as post,
        ):
            # Una redirección es un error: no se sigue.
            with self.assertRaisesRegex(RuntimeError, "302"):
                # Llamada que debe fallar.
                chat_local("incidencia", model="demo", native=False)
            # La petición se hizo sin seguir redirecciones.
            self.assertFalse(post.call_args.kwargs["allow_redirects"])
            # No se lee el cuerpo de la redirección.
            value.iter_content.assert_not_called()
            # La respuesta se cierra exactamente una vez.
            value.close.assert_called_once()
        # Respuesta de Google sin candidatos (contenido bloqueado).
        value = response(
            {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
        )
        # Sesión simulada: devuelve una respuesta controlada y permite verificar petición y cierre sin Google.
        session = Mock()
        # La sesión simulada devuelve esa respuesta al llamar a post.
        session.post.return_value = value
        # Proyecto ficticio, credenciales simuladas y sesión simulada.
        with (
            patch("curso.remote.load_config"),
            patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "demo"}),
            patch("google.auth.default", return_value=(Mock(), None)),
            patch(
                "google.auth.transport.requests.AuthorizedSession", return_value=session
            ),
        ):
            # Sin candidatos no hay respuesta: se lanza ValueError.
            with self.assertRaisesRegex(ValueError, "candidato"):
                # Llamada que debe fallar.
                chat_google("incidencia", "demo")
            # La respuesta se cerró una vez.
            value.close.assert_called_once()
            # La sesión autenticada también se cierra.
            session.close.assert_called_once()

    # Comprueba que el lector reconoce UTF-8 con BOM, UTF-16 y UTF-32.
    def test_json_bom_and_utf_encodings_remain_supported(self):
        # Texto con llaves y corchetes dentro de una cadena.
        data = {"text": "Información con [{ comillas }]"}
        # Tres codificaciones que la especificación JSON admite.
        for encoding in ("utf-8-sig", "utf-16", "utf-32"):
            # subTest informa por separado de cada codificación si alguna falla.
            with self.subTest(encoding=encoding):
                # Leer cada codificación devuelve el mismo diccionario.
                self.assertEqual(
                    bounded_json(response(chunks=[json.dumps(data).encode(encoding)])),
                    data,
                )

    # Comprueba que el catálogo y preflight usan lectura acotada y rechazan IDs inválidos.
    def test_catalog_discovery_and_preflight_use_bounded_reader(self):
        # Catálogo de LM Studio con un único modelo.
        listing = response({"data": [{"id": "demo"}]})
        # Respuesta de chat compatible con un texto conocido.
        answer = response({"choices": [{"message": {"content": "exact text"}}]})
        # load_config simulado, entorno vacío y red simulada.
        with (
            patch("curso.remote.load_config"),
            patch.dict("os.environ", {}, clear=True),
            patch("requests.get", return_value=listing) as get,
            patch("requests.post", return_value=answer),
        ):
            # Sin --modelo se usa el único modelo del catálogo y el texto llega igual.
            self.assertEqual(
                chat_local("incidencia", native=False)["respuesta_original"],
                "exact text",
            )
            # El catálogo se pidió con stream=True.
            self.assertTrue(get.call_args.kwargs["stream"])
            # Y sin seguir redirecciones.
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
        # Catálogo mal formado: una entrada sin id.
        malformed = response({"data": [{}]})
        # Buffer donde se captura el informe que imprime preflight.
        out = io.StringIO()
        # Argumentos simulados, .env ignorado, red simulada y salida capturada.
        with (
            patch("sys.argv", ["preflight", "--local"]),
            patch("preflight.load_config"),
            patch("requests.get", return_value=malformed) as get,
            redirect_stdout(out),
        ):
            # Ejecuta preflight con --local y el catálogo simulado.
            preflight_main()
        # El informe marca el catálogo como inválido en lugar de fallar.
        self.assertIn("inválida", json.loads(out.getvalue())["modelos_locales"])
        # stream=True.
        self.assertTrue(get.call_args.kwargs["stream"])
        # Sin seguir redirecciones.
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    # Distingue llaves dentro de texto y estructura anidada y aplica límites del validador.
    def test_json_size_depth_and_quoted_braces(self):
        # Objetivo ficticio con el que se valoran las respuestas de prueba.
        expected = {
            # Objetivo cuya respuesta contiene llaves y comillas dentro del texto.
            "categoria": "consulta",
            "prioridad": "baja",
            "respuesta": '[{{ texto "citado" }}]',
        }
        # El objetivo es válido aunque su texto contenga llaves y corchetes.
        self.assertTrue(
            validate_answer(json.dumps(expected), expected)["esquema_valido"]
        )
        # Tres respuestas inválidas: 33 niveles de anidamiento, texto demasiado largo y None.
        for raw in ("[" * 33 + "0" + "]" * 33, "x" * (MAX_MODEL_TEXT_CHARS + 1), None):
            # Ninguna se acepta como JSON válido.
            self.assertFalse(validate_answer(raw, expected)["json_valido"])
        # Cuerpo HTTP con 33 niveles de anidamiento (el límite es 32).
        invalid = response(chunks=[b"[" * 33 + b"0" + b"]" * 33])
        # El lector HTTP rechaza el anidamiento excesivo.
        with self.assertRaisesRegex(ValueError, "profundidad"):
            # Llamada que debe fallar.
            bounded_json(invalid)
        # La respuesta se cerró una vez.
        invalid.close.assert_called_once()

    # Comprueba protección de fórmulas en CSV y conservación exacta de los originales en JSON.
    def test_csv_neutralizes_text_and_preserves_json_evidence(self):
        # Textos que una hoja de cálculo interpretaría como fórmula:
        for value in (
            # =, +, - y @ al principio,
            "=1+1",
            "+1",
            "-1",
            "@SUM(1)",
            # también con espacios, tabuladores o saltos de línea delante
            "  =1+1",
            "\t=1+1",
            "\r=1+1",
            "\n=1+1",
            # y fórmulas con texto en varias líneas.
            "=SUM(1,2)\nnext",
        ):
            # Se antepone un apóstrofo para que la hoja de cálculo lo muestre como texto.
            self.assertEqual(csv_text(value), "'" + value)
        # Valores normales: el CSV los escribe tal cual.
        for value in ("normal", "", 1, -1, None):
            # Cada valor sale igual que entró.
            self.assertEqual(csv_text(value), value)
        # Carpeta temporal: los resultados reales no se tocan.
        with tempfile.TemporaryDirectory() as tmp:
            # Carpeta temporal con resultados simulados y su informe.
            folder = Path(tmp)
            # Lote simulado de 30 casos de test cuyos textos empiezan como fórmulas de hoja de cálculo.
            records = []
            # Recorre los 30 casos reales de test.
            for row in read_jsonl(ROOT / "datos/test.jsonl"):
                # Registro simulado con respuesta y proveedor que parecen fórmulas.
                records.append(
                    {
                        # Campos del caso: id, familia, incidencia y objetivo.
                        **row,
                        "split": "test",
                        "condicion": "qwen_base",
                        "experimento": assert_frozen(),
                        "respuesta_original": "=1+1",
                        "provider": " @SUM(1)",
                        "latencia_s": None,
                        "coste_usd": None,
                        "valoracion": validate_answer("=1+1", row["objetivo"]),
                    }
                )
            # Guarda el lote como si fuera el resultado de qwen_base.
            write_jsonl(folder / "qwen_base.jsonl", records)
            # Argumentos simulados para resumir.py y salida descartada.
            with (
                patch(
                    "sys.argv",
                    ["resumir", "--carpeta", tmp, "--destino", tmp + "/report"],
                ),
                redirect_stdout(io.StringIO()),
            ):
                # Ejecuta resumir.py sobre la carpeta temporal.
                summarize_main()
            # Abre el CSV generado; with lo cierra al terminar.
            with (folder / "report/resultados.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                # Primera fila de datos del CSV como diccionario.
                first = next(csv.DictReader(file))
            # En el CSV la fórmula aparece neutralizada.
            self.assertEqual(first["respuesta_original"], "'=1+1")
            # También en la columna provider.
            self.assertEqual(first["provider"], "' @SUM(1)")
            # Registros guardados en resultados.json.
            saved = json.loads(
                (folder / "report/resultados.json").read_text(encoding="utf-8")
            )
            # En el JSON el texto original se conserva exacto.
            self.assertEqual(saved[0]["respuesta_original"], "=1+1")
            # Sin modificar tampoco el proveedor.
            self.assertEqual(saved[0]["provider"], " @SUM(1)")
            # El informe conserva los 30 casos.
            self.assertEqual(len(saved), 30)

    # Conserva una respuesta demasiado larga como evidencia, pero la marca inválida.
    def test_overlong_bounded_model_text_survives_evaluation_and_report(self):
        # Respuesta simulada un carácter más larga que el límite del validador.
        raw = "x" * (MAX_MODEL_TEXT_CHARS + 1)
        # Carpeta temporal: los resultados reales no se tocan.
        with tempfile.TemporaryDirectory() as tmp:
            # Archivo de resultados que escribirá la evaluación remota simulada.
            path = Path(tmp) / "claude_prompt.jsonl"
            # Argumentos de un lote de test, clave ficticia y proveedor simulado.
            with (
                patch(
                    "sys.argv",
                    [
                        "evaluar",
                        "--condicion",
                        "claude_prompt",
                        "--proveedor",
                        "anthropic",
                        "--modelo",
                        "demo",
                        "--split",
                        "test",
                        "--salida",
                        str(path),
                    ],
                ),
                # Clave ficticia: la comprobación previa de credenciales no llega a la red.
                patch.dict("os.environ", {"ANTHROPIC_API_KEY": "dummy"}),
                patch(
                    "evaluar_remotos.chat",
                    return_value={
                        "respuesta_original": raw,
                        "latencia_s": 1,
                        "coste_usd": None,
                    },
                ),
                redirect_stdout(io.StringIO()),
            ):
                # Ejecuta el lote completo de test con el proveedor simulado.
                evaluate_main()
            # Resultados guardados por la evaluación simulada.
            rows = read_jsonl(path)
            # Se guardaron los 30 casos.
            self.assertEqual(len(rows), 30)
            # Todos conservan el texto completo y todos se marcan como JSON inválido.
            self.assertTrue(
                all(
                    row["respuesta_original"] == raw
                    and not row["valoracion"]["json_valido"]
                    for row in rows
                )
            )
            # Argumentos simulados para resumir.py y salida descartada.
            with (
                patch(
                    "sys.argv",
                    ["resumir", "--carpeta", tmp, "--destino", tmp + "/report"],
                ),
                redirect_stdout(io.StringIO()),
            ):
                # Genera el informe con ese lote.
                summarize_main()
            # Registros del informe JSON.
            saved = json.loads(
                (Path(tmp) / "report/resultados.json").read_text(encoding="utf-8")
            )
            # El informe conserva el texto completo.
            self.assertEqual(saved[0]["respuesta_original"], raw)


# Punto de entrada: ejecutar como script llama main; importar el módulo solo define sus funciones.
if __name__ == "__main__":
    # Ejecuta las pruebas de este archivo.
    unittest.main()
