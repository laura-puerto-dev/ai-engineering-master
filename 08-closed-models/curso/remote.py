# GUÍA DE LECTURA · curso/remote.py
# Adaptadores de inferencia remota y local, independientes del proveedor.
# chat() lee LLM_PROVIDER y LLM_MODEL del .env y llama al adaptador de esa ruta.
# Rutas: Anthropic (SDK oficial), OpenAI, OpenRouter, cualquier API compatible con
# Chat Completions, Gemini API con clave, LM Studio y Vertex AI en Google Cloud.
# Cada proveedor tiene su propia estructura de petición y de respuesta.
# Todos conservan texto original, parámetros solicitados y consumo disponible.
# La configuración se lee al llamar; importar este módulo no consulta una API.
# Google Cloud necesita un proyecto explícito del laboratorio; ninguna ruta realiza tuning.

"""Inferencia sin reparaciones, reintentos ni clientes creados al importar."""

# Convierte entre texto JSON y diccionarios/listas Python, manteniendo respuestas como evidencia.
import json

# Lee configuración del entorno y ajusta opciones del proceso.
import os

# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import time

# lru_cache recuerda el resultado de una función para no repetir una descarga con los mismos argumentos.
from functools import lru_cache

# Codifica el ID del modelo dentro de una URL y analiza URLs base configuradas en .env.
from urllib.parse import quote, urlsplit

# Constantes y utilidades compartidas del curso: raíz, límite de salida y constructor de mensajes.
from .common import ROOT, MAX_NEW_TOKENS, messages

# Lectura acotada y validada de respuestas HTTP (ver curso/http.py).
from .http import (
    bounded_json,
    objects,
    model_ids,
    model_text,
    joined_text,
    first_choice,
)


# Rutas que admite chat(); la clave es el valor de LLM_PROVIDER o de --proveedor.
PROVEEDORES = {
    "anthropic": "Messages API de Anthropic con el SDK oficial",
    "openai": "Chat Completions de OpenAI",
    "openrouter": "OpenRouter, interfaz común para muchos proveedores",
    "compatible": "Cualquier API compatible con Chat Completions (COMPAT_BASE_URL)",
    "gemini": "Gemini API de Google con clave (GEMINI_API_KEY)",
    "local": "LM Studio en tu equipo",
    "google": "Vertex AI en el proyecto Google Cloud del laboratorio",
}
# Ruta del curso cuando .env no indica otra: Claude Haiku 5.5 por la API de Anthropic.
PROVEEDOR_POR_DEFECTO = "anthropic"
# ID del modelo del curso en la API de Anthropic.
MODELO_POR_DEFECTO = "claude-haiku-5-5"
# Campos que identifican la petición; LLM_EXTRA_BODY no puede sustituirlos.
CAMPOS_PROTEGIDOS = {
    "model",
    "messages",
    "system",
    "contents",
    "systemInstruction",
    "stream",
    "input",
    "system_prompt",
}
# Variables que habilitan cada ruta: basta con una de cada tupla. LM Studio (local) no
# necesita ninguna. require_credentials y scripts/preflight.py usan esta misma tabla.
CREDENCIALES = {
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
    "openai": ("OPENAI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "compatible": ("COMPAT_BASE_URL",),
    "google": ("GOOGLE_CLOUD_PROJECT",),
}


# Lee .env si existe, conservando las variables ya definidas en el proceso.
# No crea clientes ni verifica credenciales; solo carga configuración.
def load_config():
    # Carga variables desde .env sin incluir claves en el código.
    from dotenv import load_dotenv

    # Lee .env sin sobrescribir configuración ya proporcionada por la terminal.
    load_dotenv(ROOT / ".env", override=False)


# Proveedor configurado en .env, o el del curso si no hay ninguno.
def configured_provider():
    # Carga las variables necesarias justo antes de decidir la ruta.
    load_config()
    # Quita espacios y pasa a minúsculas: «Anthropic » y «anthropic» son la misma ruta.
    return (os.getenv("LLM_PROVIDER") or PROVEEDOR_POR_DEFECTO).strip().lower()


# Modelo de LLM_MODEL; sin él, el del curso solo si la ruta es la del curso.
def configured_model():
    # Proveedor de .env; LLM_MODEL pertenece a esa ruta.
    provider = configured_provider()
    # Sin LLM_MODEL, otra ruta devuelve None y route() pedirá --modelo.
    return os.getenv("LLM_MODEL") or (
        MODELO_POR_DEFECTO if provider == PROVEEDOR_POR_DEFECTO else None
    )


# Decide proveedor y modelo: argumentos explícitos primero y, si faltan, .env.
# LLM_MODEL solo se aplica al proveedor de LLM_PROVIDER para no mezclar IDs de rutas distintas.
def route(provider=None, model=None):
    # Proveedor que el usuario dejó configurado en .env.
    configured = configured_provider()
    # Prioriza --proveedor; si falta, usa la ruta de .env.
    provider = (provider or configured).strip().lower()
    # Validación previa: rutas desconocidas fallan antes de construir una petición.
    if provider not in PROVEEDORES:
        # Detiene la ejecución y enumera las rutas válidas.
        raise ValueError(
            f"Proveedor desconocido {provider!r}; usa uno de: {', '.join(PROVEEDORES)}"
        )
    # Completa el modelo desde .env solo cuando la ruta coincide con la configurada.
    if not model and provider == configured:
        # Toma LLM_MODEL (o el modelo del curso si la ruta es la del curso).
        model = configured_model()
    # Validación previa: salvo LM Studio, que puede descubrirlo, el modelo debe ser explícito.
    if not model and provider != "local":
        # Detiene la ejecución: sin modelo no se sabe qué consultar.
        raise ValueError(f"Indica el modelo de {provider} con --modelo o LLM_MODEL")
    # Tupla (proveedor, modelo) lista para chat().
    return provider, model


# Credencial o configuración mínima de cada ruta, comprobada antes de un lote.
# Evita registrar 30 errores iguales cuando falta la clave; no muestra valores.
def require_credentials(provider):
    # Carga las variables necesarias justo antes de comprobarlas.
    load_config()
    # Variables admitidas para esta ruta; una ruta sin entrada (local) no necesita ninguna.
    needed = CREDENCIALES.get(provider, ())
    # Validación previa: basta con una de las variables admitidas para esa ruta.
    if needed and not any(os.getenv(name) for name in needed):
        # Mensaje con el nombre de la variable que falta, nunca con valores.
        raise ValueError(f"Falta {needed[0]} para la ruta {provider}")


# Ajustes opcionales del .env para la ruta configurada: temperatura y campos extra.
# Devuelve ("defecto", {}) cuando la ruta no es la de .env, para no aplicarle opciones ajenas.
def route_settings(provider):
    # Solo la ruta de LLM_PROVIDER recibe LLM_TEMPERATURE y LLM_EXTRA_BODY.
    if provider != configured_provider():
        # Ruta distinta de la de .env: valores por defecto del adaptador y ningún campo extra.
        return "defecto", {}
    # Texto de LLM_TEMPERATURE: vacío conserva el valor del adaptador; "omitir" no la envía.
    raw = (os.getenv("LLM_TEMPERATURE") or "").strip().lower()
    # Variable vacía: se usa la temperatura que fija cada adaptador.
    if not raw:
        # Valor especial: cada adaptador decide su temperatura.
        temperature = "defecto"
    # Palabras que piden no enviar temperatura en la petición.
    elif raw in ("omitir", "none", "null"):
        # None: el campo temperature no se enviará.
        temperature = None
    else:
        # Cualquier otro texto se convierte en número; por ejemplo, "0.2" pasa a 0.2.
        temperature = float(raw)
    # Campos adicionales en JSON, por ejemplo reasoning_effort o thinkingConfig de un proveedor.
    text = (os.getenv("LLM_EXTRA_BODY") or "").strip()
    # Texto vacío equivale a no añadir campos; si no, se interpreta como JSON.
    extra = json.loads(text) if text else {}
    # Validación previa: debe ser un objeto JSON y no puede reemplazar modelo ni mensajes.
    if not isinstance(extra, dict):
        # Detiene la ejecución: una lista o un número no son campos con nombre.
        raise ValueError("LLM_EXTRA_BODY debe ser un objeto JSON")
    # Intersección de conjuntos: campos de LLM_EXTRA_BODY que intentarían pisar campos protegidos.
    blocked = CAMPOS_PROTEGIDOS & set(extra)
    # Algún campo protegido aparece en LLM_EXTRA_BODY: se rechaza.
    if blocked:
        # Detiene la ejecución nombrando los campos no permitidos.
        raise ValueError(f"LLM_EXTRA_BODY no puede cambiar {sorted(blocked)}")
    # Tupla (temperatura, campos extra) que usa cada adaptador.
    return temperature, extra


# Mezcla diccionarios anidados: los valores de extra sustituyen o completan a los de base.
# Un valor null en extra elimina ese campo de la petición.
def merged(base, extra):
    # Copia superficial para no modificar el diccionario recibido.
    result = dict(base)
    # Recorre cada campo de extra junto con su valor.
    for key, value in extra.items():
        # null en LLM_EXTRA_BODY retira un campo que el adaptador enviaría por defecto.
        if value is None:
            # pop con None como segundo argumento no falla si el campo no existía.
            result.pop(key, None)
        # Si ambos son objetos, combina sus claves en lugar de reemplazar el objeto entero.
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            # Llamada recursiva: mezcla el objeto interior con la misma regla.
            result[key] = merged(result[key], value)
        # Cualquier otro valor sustituye o añade ese campo.
        else:
            # Asigna el valor de extra a ese campo.
            result[key] = value
    # Diccionario nuevo con la mezcla; base no se ha modificado.
    return result


# Coste calculado con la tarifa declarada en .env para el modelo de LLM_MODEL.
# Devuelve (None, motivo) si no hay tarifa o si el modelo usado es otro.
def tariff_cost(provider, model, tokens_in, tokens_out):
    # Tarifas en dólares por millón de tokens, escritas por el usuario en .env.
    price_in = os.getenv("LLM_PRECIO_ENTRADA_USD_MTOK")
    # Precio de los tokens de salida (la respuesta), normalmente más caro que el de entrada.
    price_out = os.getenv("LLM_PRECIO_SALIDA_USD_MTOK")
    # Solo aplica la tarifa a la ruta y el modelo para los que se declaró.
    same_route = provider == configured_provider() and model == configured_model()
    # Sin tarifa, ruta distinta o tokens desconocidos: el coste queda sin medir.
    if not (price_in and price_out and same_route) or None in (tokens_in, tokens_out):
        # (None, motivo): coste desconocido, nunca 0.
        return None, "Sin tarifa aplicable en .env; calcular tokens × precio publicado"
    # Importe en dólares: tokens de entrada y de salida por su precio por millón.
    cost = (tokens_in * float(price_in) + tokens_out * float(price_out)) / 1_000_000
    # (coste en USD, método usado para calcularlo).
    return cost, "tokens × tarifa de .env (LLM_PRECIO_*); verificar el precio vigente"


# Punto de entrada común: decide la ruta y llama a su adaptador.
# fewshot añade los cuatro ejemplos fijados de train; no entrena ningún modelo.
def chat(incident, provider=None, model=None, fewshot=False):
    # Proveedor y modelo resueltos desde argumentos o .env.
    provider, model = route(provider, model)
    # Cada ruta conserva su propio formato de petición y respuesta.
    if provider == "anthropic":
        # chat_anthropic arma la petición Messages y devuelve el registro con texto, tokens y coste.
        return chat_anthropic(incident, model, fewshot)
    # OpenAI por Chat Completions.
    if provider == "openai":
        # max_completion_tokens y sin temperatura por defecto.
        return chat_openai(incident, model, fewshot)
    # OpenRouter: un único endpoint para modelos de muchos proveedores.
    if provider == "openrouter":
        # Pide además el importe (usage.cost) a OpenRouter.
        return chat_openrouter(incident, model, fewshot)
    # Servidor compatible con Chat Completions (Groq, Ollama, vLLM…).
    if provider == "compatible":
        # URL y clave salen de COMPAT_BASE_URL y COMPAT_API_KEY.
        return chat_compatible(incident, model, fewshot)
    # Gemini API con clave de Google AI Studio.
    if provider == "gemini":
        # Usa el formato generateContent, distinto de Chat Completions.
        return chat_gemini(incident, model, fewshot)
    # LM Studio usa su API nativa salvo con few-shot, que necesita la interfaz compatible.
    if provider == "local":
        # native=True usa la API propia de LM Studio; few-shot obliga a usar la compatible.
        return chat_local(incident, model, fewshot, native=not fewshot)
    # Vertex AI: base o recurso ajustado del laboratorio; la condición del ejercicio es sin few-shot.
    if fewshot:
        # Detiene la ejecución: esta condición no admite few-shot.
        raise ValueError(
            "La ruta google del ejercicio usa el prompt básico, sin few-shot"
        )
    # Única ruta restante: google (Vertex AI).
    return chat_google(incident, model)


# Envía una incidencia a Claude por la Messages API con el SDK oficial de Anthropic.
# max_retries=0 conserva el protocolo: un fallo cuenta como error, sin reintentos.
def chat_anthropic(incident, model, fewshot=False):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Validación previa: sin credencial no se construye el cliente.
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        # Mensaje con el nombre de la variable; nunca su valor.
        raise ValueError("Falta ANTHROPIC_API_KEY")
    # SDK oficial; se importa al llamar para que importar curso.remote no conecte.
    import anthropic

    # Mensajes comunes: el primero es system y el resto alterna user/assistant y acaba en user.
    conversation = messages(incident, fewshot)
    # Claude recibe las instrucciones en el campo system, fuera de messages.
    request = {
        # ID del modelo, por ejemplo claude-haiku-5-5.
        "model": model,
        # Límite de tokens de la respuesta (180, como en S7).
        "max_tokens": MAX_NEW_TOKENS,
        # Instrucciones comunes del curso (prompts/basico.txt).
        "system": conversation[0]["content"],
        # Conversación: few-shot opcional y la incidencia nueva, en turnos user/assistant.
        "messages": conversation[1:],
        # Sin razonamiento extendido: los 180 tokens de salida quedan para la respuesta.
        "thinking": {"type": "disabled"},
    }
    # Opciones de .env: temperatura y campos extra (por ejemplo, otro thinking u output_config).
    temperature, extra = route_settings("anthropic")
    # Haiku 5.5 rechaza temperaturas distintas de la predeterminada: solo se envía si .env la fija.
    if temperature not in ("defecto", None):
        # Temperatura numérica indicada en LLM_TEMPERATURE.
        request["temperature"] = temperature
    # thinking puede sustituirse o retirarse desde .env; el resto viaja como extra_body.
    if "thinking" in extra:
        # null en LLM_EXTRA_BODY: no se envía el campo thinking.
        if extra["thinking"] is None:
            # Retira thinking de la petición.
            request.pop("thinking")
        else:
            # Usa la configuración de thinking escrita en .env.
            request["thinking"] = extra["thinking"]
    # El resto de LLM_EXTRA_BODY viaja en extra_body: el SDK lo añade tal cual al JSON enviado.
    extra_body = {k: v for k, v in extra.items() if k != "thinking"}
    # Cliente sin reintentos automáticos y con un tiempo máximo de un minuto.
    client = anthropic.Anthropic(max_retries=0, timeout=60.0)
    # Inicio de la medida temporal alrededor de la llamada completa.
    start = time.perf_counter()
    # try/except traduce los errores del SDK a mensajes del curso; finally cierra el cliente.
    try:
        # Llamada real a la API: aquí se envía la petición y se espera la respuesta completa.
        message = client.messages.create(**request, extra_body=extra_body or None)
    # Errores HTTP del servicio: se registra el estado y no se reintenta ni se cambia de modelo.
    except anthropic.APIStatusError as exc:
        # from None oculta la traza interna del SDK; el mensaje basta para registrar el error.
        raise RuntimeError(
            f"Anthropic HTTP {exc.status_code}; no se reintenta ni cambia el modelo"
        ) from None
    # Fallo de red o tiempo agotado antes de recibir respuesta.
    except anthropic.APIConnectionError:
        # from None oculta la traza interna del SDK; el caso se registrará como error.
        raise RuntimeError("Anthropic sin respuesta; no se reintenta") from None
    finally:
        # Cierra las conexiones del cliente aunque la llamada haya fallado.
        client.close()
    # Texto original: solo bloques de tipo text, en orden; los bloques thinking no son respuesta.
    raw = "".join(block.text for block in message.content if block.type == "text")
    # Tokens informados por Anthropic para esta petición.
    tokens_in, tokens_out = message.usage.input_tokens, message.usage.output_tokens
    # La API no devuelve importe: se calcula con la tarifa declarada en .env, si existe.
    cost, method = tariff_cost("anthropic", model, tokens_in, tokens_out)
    # Registro común de la consulta: los mismos campos que el resto de rutas.
    return {
        # Texto tal como llegó, sin reparar.
        "respuesta_original": raw,
        # Segundos desde el envío hasta recibir la respuesta completa.
        "latencia_s": time.perf_counter() - start,
        # Tokens que Anthropic contó en la entrada y en la salida.
        "tokens_entrada": tokens_in,
        "tokens_salida": tokens_out,
        # Coste calculado y cómo se calculó.
        "coste_usd": cost,
        "coste_metodo": method,
        # Modelo que respondió según la API.
        "model": message.model,
        # Proveedor y ruta del curso usados.
        "provider": "Anthropic",
        "ruta": "anthropic",
        # request-id de la cabecera HTTP e ID del mensaje, útiles para trazar una llamada.
        "request_id": message._request_id,
        "message_id": message.id,
        # Registra opciones solicitadas sin las instrucciones ni los mensajes.
        "parametros_solicitados": {
            **{k: v for k, v in request.items() if k not in ("system", "messages")},
            **extra_body,
        },
        # end_turn, max_tokens o refusal; con refusal no llega el JSON pedido y el validador lo marca inválido.
        "finish_reason": message.stop_reason,
    }


# Comprueba la URL base de una API configurada en .env antes de enviarle una clave.
# https es obligatorio salvo para servidores del propio equipo (Ollama, vLLM, LM Studio).
def checked_base_url(name, base_url):
    # Partes de la URL: esquema y servidor deciden si es aceptable.
    parts = urlsplit(base_url or "")
    # Validación previa: una URL sin esquema o sin servidor no se puede consultar.
    if parts.scheme not in ("http", "https") or not parts.hostname:
        # Detiene la ejecución con el nombre de la variable y el formato esperado.
        raise ValueError(f"Falta {name} con http(s)://servidor/…")
    # Las claves solo viajan sin cifrar hacia servidores de tu propio equipo.
    if parts.scheme == "http" and parts.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        # Detiene la ejecución: no se enviaría una clave sin cifrar a otro equipo.
        raise ValueError(f"{name} remota debe usar https")
    # URL aceptada, sin cambios.
    return base_url


# Petición Chat Completions común a OpenAI, OpenRouter y APIs compatibles.
# token_field cambia según el proveedor: max_tokens o max_completion_tokens.
def chat_completions(
    # Texto de la incidencia que se clasifica.
    incident,
    # ID del modelo en esta ruta.
    model,
    # True añade los cuatro ejemplos fijados de train.
    fewshot,
    # * obliga a pasar por nombre los argumentos siguientes (provider=..., key=...).
    *,
    # Nombre de la ruta: openai, openrouter o compatible.
    provider,
    # URL base de la API, sin /chat/completions.
    base_url,
    # Clave de la API; None si el servidor no la pide.
    key,
    # Nombre del límite de salida que acepta esta API.
    token_field="max_tokens",
    # Temperatura por defecto del adaptador; None no la envía.
    temperature=0,
    # Campos propios de la ruta que se añaden al cuerpo.
    defaults=None,
    # Cabeceras HTTP adicionales.
    headers=None,
):
    # Cliente HTTP; las peticiones se realizan al llamarlo, no por el simple import.
    import requests

    # Cuerpo de la petición: instrucciones, entradas y parámetros con los nombres que exige esta API.
    payload = {
        # ID del modelo.
        "model": model,
        # Conversación completa (system, few-shot opcional e incidencia).
        "messages": messages(incident, fewshot),
        # Límite de salida con el nombre que use esta API.
        token_field: MAX_NEW_TOKENS,
        # Campos propios de la ruta (por ejemplo, los de OpenRouter).
        **(defaults or {}),
    }
    # Opciones de .env: temperatura y campos extra, solo para la ruta configurada.
    env_temperature, extra = route_settings(provider)
    # Temperatura del adaptador salvo que .env la cambie u ordene omitirla.
    temperature = temperature if env_temperature == "defecto" else env_temperature
    # None significa no enviar el campo temperature.
    if temperature is not None:
        # Añade la temperatura al cuerpo de la petición.
        payload["temperature"] = temperature
    # Combina los campos extra de .env con los del adaptador.
    payload = merged(payload, extra)
    # Cabeceras: autenticación Bearer solo si hay clave; los servidores locales pueden no pedirla.
    sent_headers = {"Content-Type": "application/json", **(headers or {})}
    # Solo con clave se añade la cabecera de autenticación.
    if key:
        # Formato Bearer: «Bearer <clave>»; la clave nunca se guarda en resultados.
        sent_headers["Authorization"] = "Bearer " + key
    # Inicio de la medida temporal alrededor de la llamada completa.
    start = time.perf_counter()
    # Timeout separa conexión/lectura; stream=True permite lectura acotada y redirects quedan desactivados.
    response = requests.post(
        # URL base + /chat/completions.
        base_url.rstrip("/") + "/chat/completions",
        headers=sent_headers,
        json=payload,
        # (10, 60): hasta 10 s para conectar y 60 s esperando datos.
        timeout=(10, 60),
        # stream=True: el cuerpo se lee después por bloques con límite de tamaño.
        stream=True,
        # Una redirección se trata como error, no se sigue.
        allow_redirects=False,
    )
    # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
    if response.status_code != 200:
        # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
        response.close()
        # Error HTTP (401 clave, 429 cuota, 400 parámetro…): se registra sin reintentar.
        raise RuntimeError(
            f"{provider} HTTP {response.status_code}; no se reintenta ni cambia el modelo"
        )
    # Lee el JSON acotado y extrae el consumo usando el nombre propio de esta API.
    data = bounded_json(response)
    # Bloque usage con los tokens; si falta, queda un diccionario vacío.
    usage = data.get("usage") or {}
    # Primera alternativa válida de la respuesta del servicio.
    choice = first_choice(data)
    # Texto original que generó el modelo; no se repara antes de valorarlo o guardarlo.
    raw = model_text(choice["message"].get("content"))
    # Tokens de entrada y salida; None si el proveedor no los informa.
    tokens_in, tokens_out = usage.get("prompt_tokens"), usage.get("completion_tokens")
    # OpenRouter informa el importe en usage.cost; en otras rutas se usa la tarifa de .env.
    if usage.get("cost") is not None:
        # Importe informado por el propio proveedor.
        cost, method = usage.get("cost"), f"usage.cost de {provider}"
    else:
        # Sin importe informado: tarifa de .env o None.
        cost, method = tariff_cost(provider, model, tokens_in, tokens_out)
    # Registro común de la consulta: los mismos campos que el resto de rutas.
    return {
        # Texto tal como llegó, sin reparar.
        "respuesta_original": raw,
        # Segundos desde el envío hasta recibir la respuesta completa.
        "latencia_s": time.perf_counter() - start,
        # Tokens informados por el proveedor; los campos ausentes se conservan como None.
        "tokens_entrada": tokens_in,
        "tokens_salida": tokens_out,
        # Coste y método de cálculo.
        "coste_usd": cost,
        "coste_metodo": method,
        # Modelo que respondió según la API.
        "model": data.get("model"),
        # OpenRouter indica qué proveedor sirvió la petición; si no, se registra la ruta.
        "provider": data.get("provider") or provider,
        "ruta": provider,
        # Identificador de la petición en el proveedor, útil para soporte.
        "request_id": data.get("id"),
        # Registra opciones solicitadas pero excluye el contenido de messages de este campo de metadatos.
        "parametros_solicitados": {
            k: v for k, v in payload.items() if k not in ("messages",)
        },
        # Motivo de parada: stop, length (límite de tokens)…
        "finish_reason": choice.get("finish_reason"),
    }


# OpenAI: Chat Completions con max_completion_tokens y sin temperatura por defecto,
# porque sus modelos de razonamiento rechazan valores distintos del predeterminado.
def chat_openai(incident, model, fewshot=False):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Clave leída desde el entorno; se usa en la cabecera de autenticación y no se incluye en resultados.
    key = os.getenv("OPENAI_API_KEY")
    # Sin clave no se envía la petición: se detiene con un mensaje claro.
    if not key:
        # Mensaje con el nombre de la variable; nunca su valor.
        raise ValueError("Falta OPENAI_API_KEY")
    # Delega en el cliente Chat Completions común con los ajustes de OpenAI.
    return chat_completions(
        incident,
        model,
        fewshot,
        # Nombre de la ruta en resultados y en route_settings.
        provider="openai",
        # URL de OpenAI o la alternativa de OPENAI_BASE_URL, comprobada antes de usarla.
        base_url=checked_base_url(
            "OPENAI_BASE_URL",
            os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
        ),
        key=key,
        # OpenAI llama así al límite de salida.
        token_field="max_completion_tokens",
        # None: no envía temperatura.
        temperature=None,
    )


# Catálogo público de OpenRouter: para cada modelo, qué parámetros admite y cómo razona.
OPENROUTER_CATALOGO = "https://openrouter.ai/api/v1/models"
# El catálogo completo ronda 1 MiB y crece con cada modelo nuevo: solo esta lectura
# admite hasta 8 MiB; el resto de respuestas HTTP mantiene el límite general.
MAX_CATALOGO_BYTES = 8 * 1024 * 1024


# Busca un modelo en el catálogo de OpenRouter y devuelve su ficha (un diccionario).
# Es una lectura gratuita, sin clave ni inferencia. lru_cache guarda el resultado por
# modelo: un lote de 30 casos descarga el catálogo una sola vez.
@lru_cache(maxsize=None)
def openrouter_model(model):
    # Cliente HTTP; las peticiones se realizan al llamarlo, no por el simple import.
    import requests

    # Misma lectura acotada que el resto de rutas: streaming, sin redirecciones y con timeout.
    response = requests.get(
        OPENROUTER_CATALOGO,
        # (10, 60): hasta 10 s para conectar y 60 s esperando datos.
        timeout=(10, 60),
        # stream=True: el cuerpo se lee después por bloques con límite de tamaño.
        stream=True,
        # Una redirección se trata como error, no se sigue.
        allow_redirects=False,
    )
    # Comprueba el estado HTTP antes de leer el cuerpo.
    if response.status_code != 200:
        # Libera la conexión antes de detenerse.
        response.close()
        # Sin catálogo no se sabe qué parámetros admite el modelo: no se envía la consulta.
        raise RuntimeError(f"Catálogo de OpenRouter HTTP {response.status_code}")
    # JSON del catálogo, leído con el límite ampliado para este archivo.
    data = bounded_json(response, max_bytes=MAX_CATALOGO_BYTES)
    # Lista de modelos; cualquier otra forma se rechaza.
    entries = data.get("data")
    # El catálogo debe traer una lista en el campo data.
    if not isinstance(entries, list):
        # Detiene el proceso: formato inesperado.
        raise ValueError("Catálogo de OpenRouter mal formado")
    # Diccionario id → ficha, ignorando entradas sin un id de texto.
    catalog = {
        entry["id"]: entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    # ID exacto o, si lleva un sufijo de enrutado (:nitro, :floor…), el modelo sin sufijo.
    entry = catalog.get(model) or catalog.get(model.split(":")[0])
    # ID inexistente: se avisa antes de gastar una llamada.
    if entry is None:
        # Mensaje con el ID y dónde copiar el correcto.
        raise ValueError(
            f"{model!r} no está en el catálogo de OpenRouter; "
            "copia el ID exacto de https://openrouter.ai/models"
        )
    # Ficha del modelo: supported_parameters, reasoning, precios…
    return entry


# Traduce la ficha del catálogo al protocolo del curso, enviando solo lo que el modelo admite.
# Devuelve (temperatura, nombre del límite de salida, configuración de razonamiento).
def openrouter_settings(model, entry):
    # Parámetros que acepta este modelo, por ejemplo temperature, max_tokens o reasoning.
    supported = set(entry.get("supported_parameters") or [])
    # Temperatura 0 como el resto de rutas; None (no se envía) si el modelo no la admite,
    # como Claude Haiku 5.5 o los GPT de razonamiento.
    temperature = 0 if "temperature" in supported else None
    # Límite de 180 tokens con el nombre que acepte el modelo; max_tokens es el habitual.
    if "max_tokens" in supported or "max_completion_tokens" not in supported:
        # Nombre estándar de Chat Completions.
        token_field = "max_tokens"
    else:
        # Algunos modelos de OpenAI solo aceptan este nombre.
        token_field = "max_completion_tokens"
    # Datos de razonamiento del catálogo: si es obligatorio y qué niveles admite.
    info = entry.get("reasoning") or {}
    # Modelo sin razonamiento configurable (por ejemplo, Llama): no se envía nada.
    if "reasoning" not in supported:
        # Sin campo reasoning en la petición.
        reasoning = None
    # Gemini: nivel mínimo, igual que thinkingLevel MINIMAL en las rutas gemini y google.
    elif model.startswith("google/"):
        # OpenRouter lo traduce al nivel más bajo que admita ese Gemini.
        reasoning = {"effort": "minimal"}
    # Razonamiento opcional (Claude Haiku, Kimi, muchos GPT, DeepSeek, Qwen…): se desactiva
    # para que los 180 tokens se dediquen a la respuesta, como en la ruta directa de Anthropic.
    elif not info.get("mandatory"):
        # enabled=False apaga el razonamiento.
        reasoning = {"enabled": False}
    # Razonamiento obligatorio (algunos GLM, Grok o GPT): no se puede apagar; se pide el
    # nivel más bajo. supported_efforts va de mayor a menor, así que el último es el mínimo.
    else:
        # Niveles admitidos, sin "none" (desactivar no está permitido aquí).
        efforts = [e for e in info.get("supported_efforts") or [] if e and e != "none"]
        # Sin lista: "minimal", que OpenRouter ajusta al nivel admitido más cercano.
        reasoning = {"effort": efforts[-1] if efforts else "minimal"}
    # Tupla (temperatura, nombre del límite, razonamiento) para chat_openrouter.
    return temperature, token_field, reasoning


# Envía una incidencia por OpenRouter y conserva respuesta y metadatos.
# Vale para cualquier modelo del catálogo (Claude, GPT, Gemini, GLM, Kimi, Qwen, Llama…):
# la petición se adapta a lo que admite cada modelo y queda registrada en parametros_solicitados.
def chat_openrouter(incident, model, fewshot=False):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Clave leída desde el entorno; se usa en la cabecera de autenticación y no se incluye en resultados.
    key = os.getenv("OPENROUTER_API_KEY")
    # Sin clave no se envía la petición: se detiene con un mensaje claro.
    if not key:
        # Mensaje con el nombre de la variable; nunca su valor.
        raise ValueError("Falta OPENROUTER_API_KEY")
    # Temperatura, límite y razonamiento que admite este modelo según el catálogo.
    temperature, token_field, reasoning = openrouter_settings(
        model, openrouter_model(model)
    )
    # usage.include pide el importe; require_parameters impide que un proveedor ignore en
    # silencio un parámetro enviado (por eso solo se envían los que el modelo admite).
    defaults = {"usage": {"include": True}, "provider": {"require_parameters": True}}
    # Solo los modelos con razonamiento configurable reciben el campo reasoning.
    if reasoning is not None:
        # Desactivado, mínimo o el nivel más bajo admitido, según openrouter_settings.
        defaults["reasoning"] = reasoning
    # Delega en el cliente Chat Completions común con los ajustes de OpenRouter.
    return chat_completions(
        incident,
        model,
        fewshot,
        provider="openrouter",
        # Endpoint fijo de OpenRouter.
        base_url="https://openrouter.ai/api/v1",
        key=key,
        # max_tokens o max_completion_tokens, según el catálogo.
        token_field=token_field,
        # 0, o None (no se envía) si el modelo no la admite; LLM_TEMPERATURE puede cambiarla.
        temperature=temperature,
        # usage, provider y reasoning definidos arriba; LLM_EXTRA_BODY puede sustituirlos.
        defaults=defaults,
        # X-Title identifica la aplicación en el panel de OpenRouter.
        headers={"X-Title": "thePower S7 S8"},
    )


# Cualquier API compatible con Chat Completions: Groq, Mistral, DeepSeek, Together,
# Ollama, vLLM… La URL base y la clave salen de COMPAT_BASE_URL y COMPAT_API_KEY.
def chat_compatible(incident, model, fewshot=False):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Delega en el cliente común; la URL se comprueba antes de enviar la clave.
    return chat_completions(
        incident,
        model,
        fewshot,
        provider="compatible",
        base_url=checked_base_url("COMPAT_BASE_URL", os.getenv("COMPAT_BASE_URL")),
        # Clave opcional: los servidores locales suelen no pedirla.
        key=os.getenv("COMPAT_API_KEY"),
        # max_tokens salvo que COMPAT_TOKEN_FIELD indique otro nombre.
        token_field=os.getenv("COMPAT_TOKEN_FIELD") or "max_tokens",
    )


# Extrae texto, tokens y metadatos de una respuesta generateContent de Gemini.
# Excluye los bloques marcados como pensamiento; no repara el texto.
def gemini_reply(data):
    # Consumo en el formato propio de Google.
    usage = data.get("usageMetadata") or {}
    # Alternativas de generación del proveedor, comprobadas como lista acotada.
    candidates = objects(data.get("candidates", []), 8)
    # Sin candidatos (por ejemplo, una petición bloqueada) no hay respuesta que valorar.
    if not candidates:
        # Detiene el proceso: el caso se registrará como error.
        raise ValueError("Google no devolvió ningún candidato")
    # Contenido de la primera alternativa; se comprobará antes de extraer bloques de texto.
    content = candidates[0].get("content", {})
    # content debe ser un objeto con la lista parts.
    if not isinstance(content, dict):
        # Detiene el proceso: formato inesperado.
        raise ValueError("Contenido Google mal formado")
    # Bloques de contenido que se recorren para reconstruir la respuesta.
    parts = objects(content.get("parts", []))
    # Registro parcial; cada ruta Google añade tiempo, coste y modelo.
    return {
        # Texto original que generó el modelo; no se repara antes de valorarlo o guardarlo.
        "respuesta_original": joined_text(
            [part for part in parts if not part.get("thought")], "text"
        ),
        # Tokens de la petición (incluye system y few-shot).
        "tokens_entrada": usage.get("promptTokenCount"),
        # Tokens generados en la respuesta.
        "tokens_salida": usage.get("candidatesTokenCount"),
        # Motivo de parada: STOP, MAX_TOKENS, SAFETY…
        "finish_reason": candidates[0].get("finishReason"),
    }


# Cuerpo generateContent: instrucciones, conversación y configuración de generación.
# few-shot convierte assistant en role=model, que es el nombre que usa Gemini.
def gemini_payload(incident, fewshot=False):
    # Mensajes comunes: el primero es system y el resto alterna user/assistant y acaba en user.
    conversation = messages(incident, fewshot)
    # Cuerpo con los nombres de campo de Gemini (camelCase).
    return {
        # Instrucciones comunes: Gemini las recibe aparte, como Claude.
        "systemInstruction": {"parts": [{"text": conversation[0]["content"]}]},
        # Turnos de la conversación; Gemini llama model al rol assistant.
        "contents": [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in conversation[1:]
        ],
        # Configuración de generación: misma temperatura y límite que el resto de rutas.
        "generationConfig": {
            # Temperatura 0: la respuesta más probable, sin variación.
            "temperature": 0,
            # Límite de 180 tokens de salida.
            "maxOutputTokens": MAX_NEW_TOKENS,
            # Pensamiento mínimo, igual que en la ruta Vertex del ejercicio.
            "thinkingConfig": {"thinkingLevel": "MINIMAL"},
        },
    }


# Gemini API de Google con clave (Google AI Studio), sin proyecto de Google Cloud.
# Para el ajuste gestionado y su modelo resultante se usa chat_google (Vertex AI).
def chat_gemini(incident, model, fewshot=False):
    # Cliente HTTP; las peticiones se realizan al llamarlo, no por el simple import.
    import requests

    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Clave leída desde el entorno; viaja en la cabecera x-goog-api-key, nunca en la URL.
    key = os.getenv("GEMINI_API_KEY")
    # Sin clave no se envía la petición.
    if not key:
        # Mensaje con el nombre de la variable; nunca su valor.
        raise ValueError("Falta GEMINI_API_KEY")
    # El ID puede llegar como models/{id}; se codifica para que no altere la ruta de la URL.
    name = quote(model.removeprefix("models/"), safe="-._")
    # Cuerpo común y opciones de .env (por ejemplo, otro thinkingLevel para modelos Pro).
    payload = gemini_payload(incident, fewshot)
    # Ajustes de .env para la ruta gemini (temperatura y campos extra).
    temperature, extra = route_settings("gemini")
    # "omitir" en .env: se quita la temperatura del cuerpo.
    if temperature is None:
        # pop elimina la clave del diccionario.
        payload["generationConfig"].pop("temperature")
    # Temperatura numérica de .env en lugar de 0.
    elif temperature != "defecto":
        # Sustituye el valor dentro de generationConfig.
        payload["generationConfig"]["temperature"] = temperature
    # Mezcla los campos extra de .env con el cuerpo.
    payload = merged(payload, extra)
    # Inicio de la medida temporal alrededor de la llamada completa.
    start = time.perf_counter()
    # Respuesta HTTP que se inspeccionará y cerrará después de leerla.
    response = requests.post(
        # Endpoint de la Gemini API: versión v1beta, modelo y método generateContent.
        f"https://generativelanguage.googleapis.com/v1beta/models/{name}:generateContent",
        # Clave en una cabecera, no en la URL, donde podría quedar en registros.
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=payload,
        # (10, 60): hasta 10 s para conectar y 60 s esperando datos.
        timeout=(10, 60),
        # stream=True: lectura posterior por bloques con límite.
        stream=True,
        # Una redirección se trata como error.
        allow_redirects=False,
    )
    # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
    if response.status_code != 200:
        # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
        response.close()
        # Error HTTP: se registra sin reintentar.
        raise RuntimeError(
            f"Gemini HTTP {response.status_code}; no se reintenta ni cambia el modelo"
        )
    # Lee el JSON acotado y separa texto, tokens y motivo de parada.
    data = bounded_json(response)
    # Texto, tokens y motivo de parada extraídos del formato de Gemini.
    reply = gemini_reply(data)
    # La API no devuelve importe: se calcula con la tarifa declarada en .env, si existe.
    cost, method = tariff_cost(
        "gemini", model, reply["tokens_entrada"], reply["tokens_salida"]
    )
    # Registro común: reply aporta texto, tokens y motivo de parada.
    return {
        **reply,
        # Segundos desde el envío hasta la respuesta completa.
        "latencia_s": time.perf_counter() - start,
        # Coste y método de cálculo.
        "coste_usd": cost,
        "coste_metodo": method,
        # Versión exacta que respondió, si la API la informa.
        "model": data.get("modelVersion") or model,
        "provider": "Google · Gemini API",
        "ruta": "gemini",
        # Identificador de la respuesta en Google.
        "request_id": data.get("responseId"),
        # Parámetros enviados, sin instrucciones ni conversación.
        "parametros_solicitados": {
            k: v
            for k, v in payload.items()
            if k not in ("contents", "systemInstruction")
        },
    }


# Consulta LM Studio mediante REST nativa o interfaz compatible.
# Si falta modelo, solo lo deduce cuando el catálogo tiene exactamente una opción.
def chat_local(incident, model=None, fewshot=False, native=True):
    # Cliente HTTP; las peticiones se realizan al llamarlo, no por el simple import.
    import requests

    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Normaliza la URL del servidor local para construir las rutas /models y /chat/completions.
    base = (os.getenv("LOCAL_BASE_URL") or "http://localhost:1234/v1").rstrip("/")
    # Prioriza el ID recibido por argumento y, si falta, el ID del entorno local.
    model = model or os.getenv("LOCAL_MODEL_ID")
    # Consulta catálogo solo si todavía no hay un modelo explícito.
    if model is None:
        # Respuesta HTTP del catálogo; enumera modelos disponibles sin generar una respuesta.
        listing = requests.get(
            base + "/models", timeout=10, stream=True, allow_redirects=False
        )
        # try/finally: el catálogo se cierra aunque falle la lectura.
        try:
            # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
            if listing.status_code != 200:
                # Detiene el proceso: LM Studio no respondió bien al catálogo.
                raise ValueError("Catálogo HTTP no disponible")
            # Extrae únicamente identificadores válidos de la respuesta acotada.
            models = model_ids(bounded_json(listing))
        finally:
            # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
            listing.close()
        # Con cero o varios modelos cargados no se adivina: hay que indicar --modelo.
        if len(models) != 1:
            # Detiene el proceso con una indicación de qué hacer.
            raise ValueError(
                "Indica --modelo; el servidor no tiene exactamente un modelo"
            )
        # Selecciona la única opción del catálogo después de descartar cero o varias opciones.
        model = models[0]
    # Elige REST v1 de LM Studio; la otra rama mantiene el esquema compatible messages.
    if native:
        # La API nativa recibe una sola entrada (input), sin turnos previos: no admite few-shot.
        if fewshot:
            # Detiene el proceso con la alternativa que sí admite few-shot.
            raise ValueError(
                "Few-shot local: utiliza --local-api openai o el runner Qwen"
            )
        # Instrucciones comunes del curso, enviadas como system_prompt en esta API.
        from .common import basic_prompt

        # Cuerpo de la API nativa: input + system_prompt, reasoning off y store=False
        # (LM Studio no guarda la conversación en el servidor).
        payload = {
            # ID del modelo cargado en LM Studio.
            "model": model,
            # La incidencia como entrada única.
            "input": incident,
            # Instrucciones comunes del curso.
            "system_prompt": basic_prompt(),
            # Sin razonamiento: los 180 tokens quedan para la respuesta.
            "reasoning": "off",
            # Temperatura 0: la respuesta más probable.
            "temperature": 0,
            # Límite de salida (nombre propio de esta API).
            "max_output_tokens": MAX_NEW_TOKENS,
            # No guarda la conversación en LM Studio.
            "store": False,
        }
        # Endpoint nativo /api/v1/chat, fuera del prefijo /v1 de la interfaz compatible.
        endpoint = base.removesuffix("/v1") + "/api/v1/chat"
    else:
        # Cuerpo compatible con Chat Completions: la misma lista messages que los demás proveedores.
        payload = {
            # ID del modelo cargado en LM Studio.
            "model": model,
            # Conversación completa con few-shot opcional.
            "messages": messages(incident, fewshot),
            # Temperatura 0: la respuesta más probable.
            "temperature": 0,
            # Límite de salida de 180 tokens.
            "max_tokens": MAX_NEW_TOKENS,
        }
        # Endpoint compatible /v1/chat/completions.
        endpoint = base + "/chat/completions"
    # Inicio de la medida temporal alrededor de la llamada completa.
    start = time.perf_counter()
    # Respuesta HTTP que se inspeccionará y cerrará después de leerla.
    response = requests.post(
        endpoint, json=payload, timeout=(10, 90), stream=True, allow_redirects=False
    )
    # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
    if response.status_code != 200:
        # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
        response.close()
        # Error HTTP: se registra sin reintentar.
        raise RuntimeError(f"LM Studio HTTP {response.status_code}")
    # Lee el JSON acotado y extrae el consumo usando el nombre propio de esta API.
    data = bounded_json(response)
    # Tokens: stats en la API nativa, usage en la compatible.
    usage = data.get("stats" if native else "usage") or {}
    # Texto original que generó el modelo; no se repara antes de valorarlo o guardarlo.
    raw = (
        joined_text(
            [x for x in objects(data.get("output", [])) if x.get("type") == "message"],
            "content",
        )
        # REST nativa devuelve bloques output; compatible devuelve choices[0].message.content.
        if native
        else model_text(first_choice(data)["message"].get("content"))
    )
    # Registro común de la consulta local.
    return {
        # Texto tal como llegó, sin reparar.
        "respuesta_original": raw,
        # Segundos de la petición completa.
        "latencia_s": time.perf_counter() - start,
        # Modelo que respondió (o el pedido, si la API no lo informa).
        "model": data.get("model", model),
        # Programa que ejecutó el modelo.
        "runtime": "LM Studio",
        # Tokens de entrada con el nombre de cada API.
        "tokens_entrada": usage.get("input_tokens" if native else "prompt_tokens"),
        # Tokens de salida con el nombre de cada API.
        "tokens_salida": usage.get(
            "total_output_tokens" if native else "completion_tokens"
        ),
        # Qué API de LM Studio se usó.
        "api": "LM Studio REST v1" if native else "OpenAI compatible",
        # Coste local no medido: None, no 0.
        "coste_usd": None,
        "coste_metodo": "Hardware/energía no medidos; sin tarifa de API",
        # Parámetros enviados, sin instrucciones ni conversación.
        "parametros_solicitados": {
            k: v
            for k, v in payload.items()
            if k not in ("messages", "input", "system_prompt")
        },
    }


# Convierte una fila de S7 al formato systemInstruction + contents de Gemini.
# user contiene la incidencia y model la respuesta objetivo; ID/familia no son mensajes.
def gemini_record(row):
    """El JSONL conserva system y la respuesta objetivo; el ID va en un archivo separado."""
    # Instrucciones comunes del curso (prompts/basico.txt).
    from .common import basic_prompt

    # La entrada es role=user y la etiqueta/JSON de entrenamiento es role=model en el formato Gemini.
    return {
        # Mismas instrucciones que en S7, en el campo propio de Gemini.
        "systemInstruction": {"parts": [{"text": basic_prompt()}]},
        # Un turno user (incidencia) y un turno model (respuesta objetivo).
        "contents": [
            {"role": "user", "parts": [{"text": row["incidencia"]}]},
            # Conserva el JSON objetivo como texto para enseñar la misma tarea y no un objeto de configuración.
            {
                "role": "model",
                "parts": [{"text": json.dumps(row["objetivo"], ensure_ascii=False)}],
            },
        ],
    }


# Construye el cliente Google solo con proyecto del laboratorio explícito.
# location selecciona la región del servicio; la autenticación procede del entorno Google.
def google_client(location=None):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Proyecto explícito del laboratorio que recibirá la llamada Google.
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    # Sin proyecto explícito se detiene: no usa el proyecto por defecto de ADC
    # (Application Default Credentials, la identidad Google configurada en el equipo).
    if not project:
        # Detiene la ejecución antes de crear ningún cliente.
        raise ValueError(
            "Falta GOOGLE_CLOUD_PROJECT del laboratorio; no se usa el proyecto ADC por defecto"
        )
    # SDK de Google Gen AI; se importa aquí para que importar curso.remote no lo cargue.
    from google import genai

    # types define objetos de configuración del SDK, como HttpOptions.
    from google.genai import types

    # Cliente Vertex AI (vertexai=True) del proyecto del laboratorio.
    return genai.Client(
        # vertexai=True: usa Vertex AI (Google Cloud) en lugar de la Gemini API con clave.
        vertexai=True,
        project=project,
        # Ubicación explícita o eu; es la región de servicio, no necesariamente la del trabajo de tuning.
        location=location or os.getenv("GEMINI_SERVING_LOCATION") or "eu",
        # Versión v1 de la API y timeout del SDK expresado en milisegundos (60 s).
        http_options=types.HttpOptions(api_version="v1", timeout=60000),
    )


# Servidor de Vertex AI para una ubicación. Las multirregiones us/eu usan
# aiplatform.us|eu.rep.googleapis.com, global usa aiplatform.googleapis.com y una
# región concreta, como europe-west4, usa europe-west4-aiplatform.googleapis.com.
def vertex_host(location):
    # Multirregión: Google procesa los datos dentro de EE. UU. (us) o de la UE (eu).
    if location in ("us", "eu"):
        # Servidor de la multirregión, por ejemplo aiplatform.eu.rep.googleapis.com.
        return f"aiplatform.{location}.rep.googleapis.com"
    # Endpoint global: Google elige qué región atiende la petición.
    if location == "global":
        # Servidor global.
        return "aiplatform.googleapis.com"
    # Región concreta: su nombre va delante del dominio.
    return f"{location}-aiplatform.googleapis.com"


# Consulta generateContent autenticado con ADC en el proyecto y ubicación indicados.
# Devuelve solo bloques de respuesta, excluyendo los bloques marcados como pensamiento.
# El SDK/REST de inferencia no crea un trabajo de tuning.
def chat_google(incident, model):
    # Carga las variables necesarias justo antes de la petición, sin mostrarlas.
    load_config()
    # Sin proyecto del laboratorio no se construye la petición.
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        # Mensaje con el nombre de la variable que falta.
        raise ValueError("Falta GOOGLE_CLOUD_PROJECT del laboratorio")
    # Cuerpo de la petición: el mismo que la Gemini API, con temperatura 0, 180 tokens y thinking MINIMAL.
    payload = gemini_payload(incident)
    # REST autenticado con ADC en lugar de los tipos del SDK: así se envía thinkingLevel
    # aunque la versión instalada del SDK todavía no lo incluya en sus tipos Python.
    import google.auth

    # AuthorizedSession: sesión de requests que añade el token de Google a cada petición.
    from google.auth.transport.requests import AuthorizedSession

    # Obtiene ADC con el scope cloud-platform; la identidad real procede del entorno Google autorizado.
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    # Proyecto del laboratorio que recibirá la llamada.
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    # Región de servicio de los modelos publicados: eu por defecto, también si .env la deja vacía.
    location = os.getenv("GEMINI_SERVING_LOCATION") or "eu"
    # Gemini 3.1 Flash-Lite se ajusta en europe-west4/us-central1, pero se sirve
    # por las multirregiones eu/us. El ID del endpoint se conserva; cambia la ubicación
    # de la ruta de inferencia, como indica la documentación de tuning de Google.
    if model.startswith("projects/"):
        # Trozos del nombre separados por "/"; la región va justo después de "locations".
        parts = model.split("/")
        # Solo si el nombre contiene locations/<región>.
        if "locations" in parts[:-1]:
            index = parts.index("locations") + 1
            # La ubicación del recurso determina la residencia; no la sustituye .env.
            location = {"europe-west4": "eu", "us-central1": "us"}.get(
                parts[index], parts[index]
            )
            parts[index] = location
        resource = "/".join(parts)
    # Modelo publicado por Google, por ejemplo gemini-3.1-flash-lite.
    else:
        # Ruta del modelo publicado dentro del proyecto y la región de servicio.
        resource = (
            f"projects/{project}/locations/{location}/publishers/google/models/{model}"
        )
    # URL completa: servidor de esa ubicación, versión v1 de la API y método generateContent.
    url = f"https://{vertex_host(location)}/v1/{resource}:generateContent"
    # Sesión HTTP que aplica la autenticación Google a las peticiones.
    session = AuthorizedSession(credentials)
    # try/finally: la sesión se cierra pase lo que pase.
    try:
        # Inicio de la medida temporal justo antes de la llamada, como en las demás rutas.
        start = time.perf_counter()
        # Respuesta HTTP que se inspeccionará y cerrará después de leerla.
        response = session.post(
            url, json=payload, timeout=60, stream=True, allow_redirects=False
        )
        # Comprueba el estado HTTP antes de tratar el cuerpo como una respuesta válida del modelo.
        if response.status_code != 200:
            # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
            response.close()
            # Error HTTP (permiso, cuota, modelo no disponible…): se registra sin reintentar.
            raise RuntimeError(f"Google HTTP {response.status_code}")
        # Lee el JSON acotado y separa texto, tokens y motivo de parada.
        reply = gemini_reply(bounded_json(response))
        # Registro común: reply aporta texto, tokens y motivo de parada.
        return {
            **reply,
            # Segundos desde el envío hasta la respuesta completa.
            "latencia_s": time.perf_counter() - start,
            # Vertex AI no devuelve importe: None, no 0.
            "coste_usd": None,
            "coste_metodo": "La API no devuelve importe; consultar facturación/tarifa por separado",
            # Recurso completo consultado (modelo publicado o ajustado).
            "model": resource,
            "provider": "Google Cloud",
            "ruta": "google",
            # Parámetros de generación enviados.
            "parametros_solicitados": payload["generationConfig"],
        }
    finally:
        # Cierra el recurso abierto; libera socket/conexión aunque el paso anterior haya fallado.
        session.close()
