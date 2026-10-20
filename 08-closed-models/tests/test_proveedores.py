# GUÍA DE LECTURA · tests/test_proveedores.py
# Contratos de la capa de proveedores de curso/remote.py.
# Comprueban cómo se elige la ruta desde .env y qué petición construye cada adaptador:
# Anthropic (SDK oficial), OpenAI, OpenRouter, APIs compatibles y Gemini API.
# Mocks sustituyen SDK y red: ninguna prueba llama a un proveedor ni usa una clave real.

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import json

# Gestiona rutas de importación y el intérprete actual de Python.
import sys

# Crea directorios temporales de prueba que se retiran al salir del contexto.
import tempfile

# Organiza pruebas y aserciones; los tests se ejecutan solo al invocarlos.
import unittest

# Buffers de memoria permiten descartar la salida de los scripts dentro de una prueba.
import io

# Captura stdout en memoria para que los scripts no ensucien la salida de las pruebas.
from contextlib import redirect_stdout

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Objetos simples con atributos, como los que devuelve el SDK de Anthropic.
from types import SimpleNamespace

# Mocks sustituyen red/configuración para probar contratos sin proveedores reales.
from unittest.mock import Mock, patch

# Errores tipados del SDK y objetos HTTP con los que se construyen.
import anthropic

# Cliente HTTP que usa el SDK de Anthropic; aquí solo construye una petición y una respuesta falsas.
import httpx2

# Añade una ruta de importación para poder reutilizar el paquete curso y los scripts del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# Constantes y funciones del curso que se comparan con lo enviado.
from curso.common import MAX_NEW_TOKENS, basic_prompt

# Funciones de curso/remote.py que se ponen a prueba.
from curso.remote import (
    CREDENCIALES,
    chat,
    openrouter_model,
    require_credentials,
    route,
    vertex_host,
)

# main de evaluar_remotos.py, para ejecutar lotes simulados.
from evaluar_remotos import main as evaluate_main

# main de preflight.py.
from preflight import main as preflight_main

# Respuesta JSON válida que devuelven los proveedores simulados.
RAW = '{"categoria": "facturacion", "prioridad": "media", "respuesta": "Indica la fecha del pago."}'


# Fabrica una respuesta HTTP simulada con el cuerpo JSON indicado.
def response(data, status=200):
    # Mock que imita una respuesta de requests con el estado indicado.
    value = Mock(status_code=status, headers={})
    # iter_content devolverá un único bloque con el JSON codificado.
    value.iter_content.return_value = [json.dumps(data).encode()]
    # Respuesta simulada lista para pasarla al código del curso.
    return value


# Catálogo de OpenRouter simulado: una respuesta HTTP con la lista data de fichas de modelo.
def catalog(*entries):
    # Misma forma que https://openrouter.ai/api/v1/models, solo con las fichas indicadas.
    return response({"data": list(entries)})


# Entorno aislado: sin .env real y solo con las variables que indica cada prueba.
def environment(**values):
    # Dos context managers que se usan juntos: with load, env:
    return (
        patch("curso.remote.load_config"),
        patch.dict("os.environ", values, clear=True),
    )


# Mensaje con la forma que devuelve client.messages.create del SDK de Anthropic.
def anthropic_message(blocks):
    # SimpleNamespace crea un objeto con estos atributos, como el mensaje real del SDK.
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=40),
        model="claude-haiku-5-5",
        id="msg_demo",
        _request_id="req_demo",
        stop_reason="end_turn",
    )


# Agrupa los contratos de la capa de proveedores.
class Providers(unittest.TestCase):
    # Sin .env se usa la ruta del curso; LLM_MODEL solo completa el proveedor de LLM_PROVIDER.
    def test_route_from_env_and_arguments(self):
        # Entorno vacío: sin LLM_PROVIDER ni LLM_MODEL.
        load, env = environment()
        # Aplica los dos parches solo dentro de este bloque.
        with load, env:
            # Sin argumentos: la ruta del curso.
            self.assertEqual(route(), ("anthropic", "claude-haiku-5-5"))
            # LM Studio puede quedarse sin modelo: lo descubre su catálogo.
            self.assertEqual(route("local"), ("local", None))
            # Otro proveedor sin modelo no hereda el ID de la ruta del curso: error.
            with self.assertRaises(ValueError):
                # Llamada que debe fallar.
                route("openai")
            # Un proveedor desconocido también falla.
            with self.assertRaises(ValueError):
                # Llamada que debe fallar.
                route("desconocido", "x")
        # .env apunta a OpenAI (con mayúsculas, que se normalizan).
        load, env = environment(LLM_PROVIDER="OpenAI", LLM_MODEL="gpt-demo")
        # Aplica los dos parches solo dentro de este bloque.
        with load, env:
            # La ruta y el modelo de .env.
            self.assertEqual(route(), ("openai", "gpt-demo"))
            # --modelo sustituye a LLM_MODEL en la misma ruta.
            self.assertEqual(route(None, "otro"), ("openai", "otro"))
            # Si .env apunta a otra ruta, pedir la del curso sin modelo es un error.
            with self.assertRaises(ValueError):
                # Llamada que debe fallar.
                route("anthropic")

    # Claude por la Messages API: system aparte, sin temperatura, sin thinking y sin reintentos.
    def test_anthropic_request_record_and_cost(self):
        # Clave ficticia y tarifa de .env para calcular el coste.
        load, env = environment(
            ANTHROPIC_API_KEY="dummy",
            LLM_PRECIO_ENTRADA_USD_MTOK="0.10",
            LLM_PRECIO_SALIDA_USD_MTOK="0.50",
        )
        # Cliente simulado: devuelve un bloque thinking vacío seguido del texto de la respuesta.
        client = Mock()
        # La llamada simulada devuelve un mensaje con un bloque thinking y otro de texto.
        client.messages.create.return_value = anthropic_message(
            [
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text=RAW),
            ]
        )
        # anthropic.Anthropic sustituido: el SDK no conecta con nadie.
        with load, env, patch("anthropic.Anthropic", return_value=client) as factory:
            # Ruta de .env (la del curso) con few-shot.
            result = chat("incidencia", fewshot=True)
        # El cliente se crea sin reintentos automáticos y se cierra al terminar.
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
        # close() se llamó una vez.
        client.close.assert_called_once()
        # Argumentos con nombre que recibió messages.create.
        sent = client.messages.create.call_args.kwargs
        # Petición: modelo del curso, 180 tokens, instrucciones en system y conversación few-shot.
        self.assertEqual(sent["model"], "claude-haiku-5-5")
        # Límite de 180 tokens.
        self.assertEqual(sent["max_tokens"], MAX_NEW_TOKENS)
        # Instrucciones comunes en el campo system.
        self.assertEqual(sent["system"], basic_prompt())
        # 4 pares few-shot + la incidencia = 9 mensajes.
        self.assertEqual(len(sent["messages"]), 9)
        # La conversación empieza por un turno user.
        self.assertEqual(sent["messages"][0]["role"], "user")
        # Y termina con la incidencia nueva.
        self.assertEqual(
            sent["messages"][-1], {"role": "user", "content": "incidencia"}
        )
        # Razonamiento extendido desactivado.
        self.assertEqual(sent["thinking"], {"type": "disabled"})
        # Haiku 5.5 rechaza temperaturas no predeterminadas: no se envía ninguna.
        self.assertNotIn("temperature", sent)
        # Sin campos extra de .env.
        self.assertIsNone(sent["extra_body"])
        # Registro: solo el texto, tokens, coste por tarifa de .env e identificadores.
        self.assertEqual(result["respuesta_original"], RAW)
        # Tokens informados por el SDK.
        self.assertEqual(
            (result["tokens_entrada"], result["tokens_salida"]), (1000, 40)
        )
        # Coste = tokens × tarifa / 1 000 000.
        self.assertAlmostEqual(result["coste_usd"], (1000 * 0.10 + 40 * 0.50) / 1e6)
        # Identificador de la petición HTTP.
        self.assertEqual(result["request_id"], "req_demo")
        # Motivo de parada.
        self.assertEqual(result["finish_reason"], "end_turn")
        # Ruta registrada.
        self.assertEqual(result["ruta"], "anthropic")
        # Las instrucciones no se copian en los parámetros registrados.
        self.assertNotIn("system", result["parametros_solicitados"])

    # Sin clave no se crea cliente; un error HTTP se registra sin reintentar.
    def test_anthropic_missing_key_and_status_error(self):
        # Entorno sin ninguna clave.
        load, env = environment()
        # Si se creara el cliente, factory lo registraría.
        with load, env, patch("anthropic.Anthropic") as factory:
            # Debe fallar.
            with self.assertRaises(ValueError):
                # Llamada con la ruta del curso.
                chat("incidencia")
            # No se llegó a crear el cliente.
            factory.assert_not_called()
        # Error 429 del servicio, construido como lo haría el SDK.
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        # Error de límite de peticiones (429) del SDK.
        error = anthropic.RateLimitError(
            "límite", response=httpx2.Response(429, request=request), body=None
        )
        # Cliente simulado cuya llamada lanza ese error.
        client = Mock()
        # side_effect: la llamada lanza el error en lugar de devolver un valor.
        client.messages.create.side_effect = error
        # Ahora sí hay clave.
        load, env = environment(ANTHROPIC_API_KEY="dummy")
        # El SDK usa el cliente simulado.
        with load, env, patch("anthropic.Anthropic", return_value=client):
            # El error del SDK se traduce a RuntimeError con el estado HTTP.
            with self.assertRaisesRegex(RuntimeError, "429"):
                # Llamada que debe fallar.
                chat("incidencia")
        # Una sola llamada: no hay reintentos.
        client.messages.create.assert_called_once()
        # El cliente se cerró igualmente.
        client.close.assert_called_once()

    # .env puede cambiar temperatura, thinking y añadir campos del proveedor configurado.
    def test_env_overrides_for_configured_route(self):
        # Temperatura 1 y campos extra en .env.
        load, env = environment(
            ANTHROPIC_API_KEY="dummy",
            LLM_TEMPERATURE="1",
            LLM_EXTRA_BODY='{"thinking": null, "output_config": {"effort": "low"}}',
        )
        # Cliente simulado.
        client = Mock()
        # Devuelve un mensaje con solo texto.
        client.messages.create.return_value = anthropic_message(
            [SimpleNamespace(type="text", text=RAW)]
        )
        # Sustituye el SDK por el cliente simulado.
        with load, env, patch("anthropic.Anthropic", return_value=client):
            # Consulta con la ruta de .env.
            chat("incidencia")
        # Argumentos enviados al SDK.
        sent = client.messages.create.call_args.kwargs
        # thinking: null en .env retiró el campo.
        self.assertNotIn("thinking", sent)
        # La temperatura de .env se envió como número.
        self.assertEqual(sent["temperature"], 1.0)
        # El resto de campos extra viaja en extra_body.
        self.assertEqual(sent["extra_body"], {"output_config": {"effort": "low"}})
        # Campos protegidos o un JSON que no es un objeto se rechazan.
        for value in ('{"model": "otro"}', "[1]"):
            # Entorno con ese LLM_EXTRA_BODY no válido.
            load, env = environment(ANTHROPIC_API_KEY="dummy", LLM_EXTRA_BODY=value)
            # Sustituye el SDK por el cliente simulado.
            with load, env, patch("anthropic.Anthropic", return_value=client):
                # Debe fallar antes de llamar.
                with self.assertRaises(ValueError):
                    # Llamada que debe fallar.
                    chat("incidencia")

    # OpenAI, APIs compatibles y OpenRouter comparten Chat Completions con nombres propios.
    def test_chat_completions_routes(self):
        # Respuesta Chat Completions simulada que comparten las tres rutas.
        envelope = {
            "id": "gen-demo",
            "model": "demo",
            "choices": [{"message": {"content": RAW}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 30},
        }
        # Clave ficticia de OpenAI.
        load, env = environment(OPENAI_API_KEY="dummy")
        # requests.post sustituido: devuelve la respuesta simulada.
        with load, env, patch("requests.post", return_value=response(envelope)) as post:
            # Ruta openai con un modelo inventado.
            result = chat("incidencia", "openai", "gpt-demo")
        # Argumentos con nombre de la petición.
        sent = post.call_args.kwargs
        # OpenAI: max_completion_tokens, sin temperatura y con autenticación Bearer.
        self.assertEqual(
            post.call_args.args[0], "https://api.openai.com/v1/chat/completions"
        )
        # Límite de salida con el nombre de OpenAI.
        self.assertEqual(sent["json"]["max_completion_tokens"], MAX_NEW_TOKENS)
        # Y no con el nombre genérico.
        self.assertNotIn("max_tokens", sent["json"])
        # Sin temperatura.
        self.assertNotIn("temperature", sent["json"])
        # Autenticación Bearer con la clave.
        self.assertEqual(sent["headers"]["Authorization"], "Bearer dummy")
        # Lectura acotada.
        self.assertTrue(sent["stream"])
        # Sin seguir redirecciones.
        self.assertFalse(sent["allow_redirects"])
        # Texto intacto.
        self.assertEqual(result["respuesta_original"], RAW)
        # Sin tarifa en .env: coste desconocido.
        self.assertIsNone(result["coste_usd"])
        # Servidor compatible en el propio equipo: sin clave y con temperatura 0.
        load, env = environment(COMPAT_BASE_URL="http://localhost:11434/v1")
        # requests.post sustituido.
        with load, env, patch("requests.post", return_value=response(envelope)) as post:
            # Ruta compatible con un modelo inventado.
            chat("incidencia", "compatible", "llama-demo")
        # URL base de .env + /chat/completions.
        self.assertEqual(
            post.call_args.args[0], "http://localhost:11434/v1/chat/completions"
        )
        # Sin clave no se envía cabecera Authorization.
        self.assertNotIn("Authorization", post.call_args.kwargs["headers"])
        # Temperatura 0 por defecto.
        self.assertEqual(post.call_args.kwargs["json"]["temperature"], 0)
        # Sin URL, o con http hacia un servidor remoto, no se envía nada.
        for url in ("", "http://proveedor.example/v1"):
            # URL vacía o remota sin https.
            load, env = environment(COMPAT_BASE_URL=url)
            # Si se enviara algo, post lo registraría.
            with load, env, patch("requests.post") as post:
                # Debe fallar.
                with self.assertRaises(ValueError):
                    # Llamada que debe fallar.
                    chat("incidencia", "compatible", "x")
                # No se envió ninguna petición.
                post.assert_not_called()
        # OpenRouter conserva usage.cost como coste informado por la ruta.
        priced = dict(envelope, usage={**envelope["usage"], "cost": 0.0002})
        # Clave ficticia de OpenRouter.
        load, env = environment(OPENROUTER_API_KEY="dummy")
        # Vacía la caché del catálogo antes y después para no mezclar pruebas.
        openrouter_model.cache_clear()
        # addCleanup ejecuta la limpieza al terminar la prueba, aunque falle.
        self.addCleanup(openrouter_model.cache_clear)
        # requests.get devuelve el catálogo y requests.post la respuesta con importe.
        with (
            load,
            env,
            patch("requests.get", return_value=catalog({"id": "proveedor/modelo"})),
            patch("requests.post", return_value=response(priced)) as post,
        ):
            # Ruta openrouter con un modelo inventado.
            result = chat("incidencia", "openrouter", "proveedor/modelo")
        # Se pidió a OpenRouter que informe del importe.
        self.assertEqual(post.call_args.kwargs["json"]["usage"], {"include": True})
        # El coste registrado es el que informó OpenRouter.
        self.assertEqual(result["coste_usd"], 0.0002)

    # OpenRouter sirve cualquier modelo: la petición se adapta a lo que admite cada uno
    # según el catálogo (temperatura, nombre del límite y razonamiento).
    def test_openrouter_adapts_request_to_catalog(self):
        # Fichas inspiradas en el catálogo real: cada una cubre un caso distinto.
        entries = [
            # Claude Haiku 5.5: sin temperatura y con razonamiento que se puede apagar.
            {
                "id": "anthropic/claude-haiku-5.5",
                "supported_parameters": ["max_tokens", "reasoning"],
                "reasoning": {"mandatory": False},
            },
            # GLM: temperatura admitida y razonamiento obligatorio con tres niveles.
            {
                "id": "z-ai/glm-5.3",
                "supported_parameters": ["max_tokens", "reasoning", "temperature"],
                "reasoning": {
                    "mandatory": True,
                    "supported_efforts": ["max", "high", "low"],
                },
            },
            # Llama: temperatura admitida y sin razonamiento configurable.
            {
                "id": "meta-llama/llama-4-maverick",
                "supported_parameters": ["max_tokens", "temperature"],
            },
            # Gemini: razonamiento opcional; el curso pide siempre el nivel mínimo.
            {
                "id": "google/gemini-3.1-flash-lite",
                "supported_parameters": ["max_tokens", "reasoning", "temperature"],
                "reasoning": {"mandatory": False},
            },
            # Un GPT que solo acepta max_completion_tokens como límite de salida.
            {
                "id": "openai/gpt-chat",
                "supported_parameters": ["max_completion_tokens"],
            },
        ]
        # Respuesta Chat Completions simulada, común a todos los modelos.
        envelope = {
            "id": "gen-demo",
            "model": "demo",
            "choices": [{"message": {"content": RAW}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 30, "cost": 0.0001},
        }
        # Lo que debe llegar a OpenRouter para cada modelo; ausente = no se envía.
        expected = {
            "anthropic/claude-haiku-5.5": {"reasoning": {"enabled": False}},
            "z-ai/glm-5.3": {"temperature": 0, "reasoning": {"effort": "low"}},
            "meta-llama/llama-4-maverick": {"temperature": 0},
            "google/gemini-3.1-flash-lite": {
                "temperature": 0,
                "reasoning": {"effort": "minimal"},
            },
            "openai/gpt-chat": {},
        }
        # Vacía la caché del catálogo antes y después para no mezclar pruebas.
        openrouter_model.cache_clear()
        # addCleanup ejecuta la limpieza al terminar la prueba, aunque falle.
        self.addCleanup(openrouter_model.cache_clear)
        # Recorre cada modelo con su petición esperada.
        for model, fields in expected.items():
            # subTest identifica el modelo si una comprobación falla.
            with self.subTest(model=model):
                # Clave ficticia de OpenRouter.
                load, env = environment(OPENROUTER_API_KEY="dummy")
                # Catálogo y respuesta simulados: no hay red.
                with (
                    load,
                    env,
                    patch("requests.get", return_value=catalog(*entries)) as get,
                    patch("requests.post", return_value=response(envelope)) as post,
                ):
                    # Consulta por la ruta openrouter con este modelo.
                    result = chat("incidencia", "openrouter", model)
                # Cuerpo JSON enviado a OpenRouter.
                sent = post.call_args.kwargs["json"]
                # El catálogo se leyó con streaming y sin seguir redirecciones.
                self.assertTrue(get.call_args.kwargs["stream"])
                # Una redirección no se sigue.
                self.assertFalse(get.call_args.kwargs["allow_redirects"])
                # Temperatura solo si el modelo la admite.
                self.assertEqual(sent.get("temperature"), fields.get("temperature"))
                # Razonamiento: apagado, mínimo, el nivel más bajo o ausente.
                self.assertEqual(sent.get("reasoning"), fields.get("reasoning"))
                # require_parameters se mantiene: OpenRouter no ignora parámetros en silencio.
                self.assertEqual(sent["provider"], {"require_parameters": True})
                # El límite de 180 tokens viaja con el nombre que admite el modelo.
                field = (
                    "max_completion_tokens"
                    if model == "openai/gpt-chat"
                    else "max_tokens"
                )
                # Valor del límite común del curso.
                self.assertEqual(sent[field], MAX_NEW_TOKENS)
                # Texto intacto.
                self.assertEqual(result["respuesta_original"], RAW)
        # Un sufijo de enrutado (:nitro) usa la ficha del modelo sin sufijo, y la caché
        # evita descargar el catálogo de nuevo para el mismo modelo.
        load, env = environment(OPENROUTER_API_KEY="dummy")
        # Dos consultas seguidas al mismo modelo con sufijo.
        with (
            load,
            env,
            patch("requests.get", return_value=catalog(*entries)) as get,
            patch("requests.post", return_value=response(envelope)) as post,
        ):
            # Primera consulta: descarga el catálogo.
            chat("incidencia", "openrouter", "z-ai/glm-5.3:nitro")
            # Segunda consulta: reutiliza la ficha guardada.
            chat("incidencia", "openrouter", "z-ai/glm-5.3:nitro")
        # Una sola descarga del catálogo para las dos consultas.
        self.assertEqual(get.call_count, 1)
        # El sufijo usa la ficha de GLM: razonamiento en su nivel más bajo.
        self.assertEqual(post.call_args.kwargs["json"]["reasoning"], {"effort": "low"})
        # Un ID que no existe se rechaza antes de gastar una llamada.
        load, env = environment(OPENROUTER_API_KEY="dummy")
        # Catálogo sin ese modelo; post no debe llamarse.
        with (
            load,
            env,
            patch("requests.get", return_value=catalog(*entries)),
            patch("requests.post") as post,
        ):
            # Debe fallar con un mensaje que nombra el ID.
            with self.assertRaisesRegex(ValueError, "no está en el catálogo"):
                # Modelo inexistente.
                chat("incidencia", "openrouter", "z-ai/glm-inventado")
        # No se envió ninguna consulta de pago.
        post.assert_not_called()
        # evaluar_remotos.py comprueba el ID antes del lote: ni llamadas ni archivo.
        with tempfile.TemporaryDirectory() as tmp:
            # Ruta del archivo de resultados que no debe crearse.
            path = Path(tmp) / "remoto.jsonl"
            # Clave ficticia de OpenRouter.
            load, env = environment(OPENROUTER_API_KEY="dummy")
            # Lote remoto_basico con un ID inexistente.
            with (
                load,
                env,
                patch(
                    "sys.argv",
                    [
                        "evaluar",
                        "--condicion",
                        "remoto_basico",
                        "--proveedor",
                        "openrouter",
                        "--modelo",
                        "z-ai/glm-inventado",
                        "--salida",
                        str(path),
                    ],
                ),
                patch("requests.get", return_value=catalog(*entries)),
                patch("evaluar_remotos.chat") as call,
                patch("sys.stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                # Debe terminar con un error de uso.
                evaluate_main()
            # Ninguna consulta.
            call.assert_not_called()
            # Ningún archivo.
            self.assertFalse(path.exists())

    # Gemini API con clave: contents user/model, thinking mínimo y bloques thought excluidos.
    def test_gemini_api_payload_and_reply(self):
        # Respuesta generateContent simulada: un bloque de pensamiento y otro de texto.
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "pienso", "thought": True}, {"text": RAW}]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 25},
            "responseId": "resp-demo",
        }
        # Clave ficticia de la Gemini API.
        load, env = environment(GEMINI_API_KEY="dummy")
        # requests.post devuelve la respuesta simulada.
        with load, env, patch("requests.post", return_value=response(data)) as post:
            # ID con el prefijo models/ y few-shot activado.
            result = chat("incidencia", "gemini", "models/gemini-3.1-flash-lite", True)
        # Argumentos con nombre de la petición.
        sent = post.call_args.kwargs
        # El prefijo models/ no se duplica en la URL.
        self.assertTrue(
            post.call_args.args[0].endswith(
                "/models/gemini-3.1-flash-lite:generateContent"
            )
        )
        # La clave viaja en la cabecera x-goog-api-key.
        self.assertEqual(sent["headers"]["x-goog-api-key"], "dummy")
        # Roles de la conversación enviada.
        roles = [m["role"] for m in sent["json"]["contents"]]
        # Cuatro pares user/model y la incidencia final.
        self.assertEqual(roles, ["user", "model"] * 4 + ["user"])
        # Pensamiento al mínimo.
        self.assertEqual(
            sent["json"]["generationConfig"]["thinkingConfig"],
            {"thinkingLevel": "MINIMAL"},
        )
        # El bloque de pensamiento no forma parte de la respuesta.
        self.assertEqual(result["respuesta_original"], RAW)
        # Tokens de usageMetadata.
        self.assertEqual((result["tokens_entrada"], result["tokens_salida"]), (300, 25))
        # Motivo de parada de Gemini.
        self.assertEqual(result["finish_reason"], "STOP")
        # La ruta Vertex del ejercicio no admite few-shot.
        load, env = environment(GOOGLE_CLOUD_PROJECT="demo")
        # Debe fallar antes de pedir credenciales.
        with load, env, self.assertRaises(ValueError):
            # Vertex AI con few-shot.
            chat("incidencia", "google", "gemini-3.1-flash-lite", True)

    # Tuning regional y serving multirregión son ubicaciones distintas para Gemini 3.1.
    def test_google_endpoint_host_and_tuned_region(self):
        # Servidor de cada tipo de ubicación según la documentación de Google Cloud.
        self.assertEqual(vertex_host("eu"), "aiplatform.eu.rep.googleapis.com")
        # Endpoint global.
        self.assertEqual(vertex_host("global"), "aiplatform.googleapis.com")
        # Región concreta.
        self.assertEqual(
            vertex_host("europe-west4"), "europe-west4-aiplatform.googleapis.com"
        )
        # Respuesta generateContent mínima que devolverá la sesión simulada.
        reply = {"candidates": [{"content": {"parts": [{"text": RAW}]}}]}
        # Recurso de un modelo ajustado: su región (europe-west4) va dentro del nombre.
        tuned = "projects/demo/locations/europe-west4/endpoints/123"
        # Pares (modelo pedido, URL que debe recibir la petición).
        cases = (
            (
                "gemini-3.1-flash-lite",
                "https://aiplatform.eu.rep.googleapis.com/v1/projects/demo/locations/eu"
                "/publishers/google/models/gemini-3.1-flash-lite:generateContent",
            ),
            (
                tuned,
                "https://aiplatform.eu.rep.googleapis.com/v1/projects/demo/locations/eu"
                "/endpoints/123:generateContent",
            ),
            (
                "projects/demo/locations/us-central1/endpoints/456",
                "https://aiplatform.us.rep.googleapis.com/v1/projects/demo/locations/us"
                "/endpoints/456:generateContent",
            ),
            (
                "projects/demo/locations/eu/endpoints/123",
                "https://aiplatform.eu.rep.googleapis.com/v1/projects/demo/locations/eu"
                "/endpoints/123:generateContent",
            ),
        )
        # Prueba base, ajustes en Europa/EE. UU. y un endpoint ya expresado en eu.
        for model, url in cases:
            # Sesión autenticada simulada: registra la URL sin conectar con Google.
            session = Mock()
            # post devolverá la respuesta generateContent simulada.
            session.post.return_value = response(reply)
            # Solo el proyecto del laboratorio; GEMINI_SERVING_LOCATION ausente usa eu.
            load, env = environment(GOOGLE_CLOUD_PROJECT="demo")
            # Credenciales y sesión simuladas: no hay red.
            with (
                load,
                env,
                patch("google.auth.default", return_value=(Mock(), None)),
                patch(
                    "google.auth.transport.requests.AuthorizedSession",
                    return_value=session,
                ),
            ):
                # Consulta por la ruta google.
                result = chat("incidencia", "google", model)
            # El texto llega intacto y la petición fue a la URL esperada.
            self.assertEqual(result["respuesta_original"], RAW)
            # URL exacta de la petición.
            self.assertEqual(session.post.call_args.args[0], url)

    # require_credentials y preflight comparten la tabla CREDENCIALES:
    # ANTHROPIC_AUTH_TOKEN también habilita la ruta de Anthropic.
    def test_credentials_table_shared_with_preflight(self):
        # Entorno aislado con una única variable: el token alternativo de Anthropic.
        load, env = environment(ANTHROPIC_AUTH_TOKEN="dummy")
        # Captura del informe JSON que preflight imprime.
        out = io.StringIO()
        # Entorno, .env, argumentos y salida simulados.
        with (
            load,
            env,
            patch("preflight.load_config"),
            patch("sys.argv", ["preflight"]),
            redirect_stdout(out),
        ):
            # Anthropic pasa la comprobación; OpenAI sigue sin credencial.
            require_credentials("anthropic")
            # Debe fallar.
            with self.assertRaises(ValueError):
                # Llamada que debe fallar.
                require_credentials("openai")
            # Ejecuta preflight y captura su informe.
            preflight_main()
        # El informe muestra solo booleanos, con una entrada por ruta salvo google.
        report = json.loads(out.getvalue())
        # Anthropic aparece configurado.
        self.assertTrue(report["credenciales"]["anthropic"])
        # OpenAI no.
        self.assertFalse(report["credenciales"]["openai"])
        # Una entrada por ruta de CREDENCIALES, salvo google.
        self.assertEqual(set(report["credenciales"]), set(CREDENCIALES) - {"google"})
        # Ningún valor secreto aparece en la salida.
        self.assertNotIn("dummy", out.getvalue())

    # La evaluación usa la ruta de .env para claude_prompt y fija la ruta de Gemini.
    def test_remote_evaluation_routes(self):
        # Carpeta temporal para el archivo de resultados.
        with tempfile.TemporaryDirectory() as tmp:
            # Ruta del archivo de resultados del lote.
            path = Path(tmp) / "claude_prompt.jsonl"
            # Sin clave, el lote se detiene antes de llamar ni escribir resultados.
            load, env = environment()
            # Entorno sin claves, argumentos simulados y chat sustituido.
            with (
                load,
                env,
                patch(
                    "sys.argv",
                    ["evaluar", "--condicion", "claude_prompt", "--salida", str(path)],
                ),
                patch("evaluar_remotos.chat") as call,
                patch("sys.stderr", io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                # Debe terminar con un error de uso.
                evaluate_main()
            # No hubo ninguna llamada.
            call.assert_not_called()
            # Ni se escribió ningún archivo.
            self.assertFalse(path.exists())
            # Ahora con clave ficticia.
            load, env = environment(ANTHROPIC_API_KEY="dummy")
            # Lote de desarrollo con un proveedor simulado que siempre responde RAW.
            with (
                load,
                env,
                patch(
                    "sys.argv",
                    [
                        "evaluar",
                        "--condicion",
                        "claude_prompt",
                        "--split",
                        "desarrollo",
                        "--salida",
                        str(path),
                    ],
                ),
                patch(
                    "evaluar_remotos.chat",
                    return_value={
                        "respuesta_original": RAW,
                        "latencia_s": 1,
                        "coste_usd": None,
                    },
                ) as call,
                redirect_stdout(io.StringIO()),
            ):
                # Ejecuta el lote completo.
                evaluate_main()
            # Seis casos de desarrollo con Claude Haiku 5.5 por Anthropic y few-shot.
            self.assertEqual(call.call_count, 6)
            # Ruta y modelo del curso, con few-shot (claude_prompt).
            self.assertEqual(
                call.call_args.args[1:], ("anthropic", "claude-haiku-5-5", True)
            )
        # Gemini del ejercicio no cambia de proveedor.
        load, env = environment()
        # gemini_base con --proveedor anthropic: debe terminar con un error de uso.
        with (
            load,
            env,
            patch(
                "sys.argv",
                [
                    "evaluar",
                    "--condicion",
                    "gemini_base",
                    "--proveedor",
                    "anthropic",
                    "--salida",
                    "x.jsonl",
                ],
            ),
            redirect_stdout(io.StringIO()),
            patch("sys.stderr", io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            # Ejecuta main() con esos argumentos.
            evaluate_main()


# Permite ejecutar este archivo directamente además de unittest discover.
if __name__ == "__main__":
    # Ejecuta las pruebas de este archivo.
    unittest.main()
