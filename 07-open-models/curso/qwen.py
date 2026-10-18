# GUÍA DE LECTURA · curso/qwen.py
# Puente entre los archivos del Hub y la inferencia local con Transformers.
# load_qwen carga la misma revisión para todas las condiciones.
# render aplica la plantilla de conversación y generate produce tokens nuevos.
# El adaptador LoRA se carga sobre la base; la inferencia no actualiza parámetros.
# Las dependencias pesadas se importan dentro de las funciones que las necesitan.

"""Inferencia y tokenización con el mismo template, sin llamadas al importar."""

# Mide duración y prepara fechas; perf_counter/monotonic sirven para intervalos, no fechas del calendario.
import time

# Modelo, revisión, parámetros de generación y constructor de mensajes compartidos.
from .common import MODEL_ID, REVISION, GENERATION, messages


# Carga tokenizer y modelo base en el dispositivo disponible.
# Si adapter tiene una ruta, aplica ese adaptador PEFT sobre la misma base.
# Devuelve modelo, tokenizer y nombre del dispositivo; todavía no genera texto.
def load_qwen(adapter=None):
    # Motor de tensores y gradientes; durante inferencia se desactivan los gradientes.
    import torch

    # Carga modelos/tokenizers y aporta generación y utilidades de entrenamiento.
    from transformers import AutoTokenizer, AutoModelForCausalLM

    # Prefiere CUDA; si no existe, MPS del Mac; como última opción utiliza CPU.
    device = (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
    # Carga vocabulario y plantilla de chat de la misma revisión; token=False no usa cuenta de
    # Hugging Face y trust_remote_code=False impide ejecutar código descargado del repositorio.
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=REVISION, token=False, trust_remote_code=False
    )
    # Carga los pesos Safetensors y los mueve al dispositivo con .to(device).
    # FP32 en MPS hace más estable y reproducible el entrenamiento de este modelo pequeño;
    # en CUDA/CPU se usa el dtype del checkpoint. "eager" es la atención estándar de PyTorch.
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=REVISION,
        dtype=torch.float32 if device == "mps" else "auto",
        attn_implementation="eager",
        token=False,
        trust_remote_code=False,
        use_safetensors=True,
    ).to(device)
    # Solo aplica PEFT si se ha solicitado un adaptador; la base sola es la condición original.
    if adapter:
        # Añade/recarga adaptadores LoRA manteniendo el modelo base separado.
        from peft import PeftModel

        # Recarga las matrices aprendidas sobre el modelo original compatible.
        model = PeftModel.from_pretrained(model, adapter)
    # Activa modo evaluación para desactivar dropout; SFTTrainer activará modo entrenamiento cuando corresponda.
    model.eval()
    # Tupla con los tres objetos: quien llama los desempaqueta con model, tokenizer, device = ...
    return model, tokenizer, device


# Convierte una lista de mensajes en texto con la plantilla oficial de Qwen.
# add_generation_prompt prepara el comienzo de la respuesta; thinking queda desactivado.
def render(tokenizer, msg, add_generation_prompt=True):
    # Marca roles y turno assistant con el template de Qwen; enable_thinking=False conserva el protocolo.
    return tokenizer.apply_chat_template(
        msg,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
        enable_thinking=False,
    )


# Genera una respuesta local usando el prompt compartido y parámetros fijados.
# Recibe incidencia y fewshot, y devuelve texto original, tokens y tiempo.
# Durante inferencia no calcula gradientes ni actualiza los pesos.
def generate(model, tokenizer, device, incident, fewshot=False):
    # Motor de tensores y gradientes; durante inferencia se desactivan los gradientes.
    import torch

    # Mensajes system/user (y few-shot si se pide) convertidos en un único texto con la plantilla de Qwen.
    text = render(tokenizer, messages(incident, fewshot))
    # Convierte el prompt en tensores y los mueve al mismo dispositivo que los pesos.
    inputs = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(device)
    # Espera a las operaciones MPS pendientes para que la medida temporal tenga límites definidos.
    if device == "mps":
        # synchronize() bloquea hasta que la GPU del Mac termina el trabajo pendiente.
        torch.mps.synchronize()
    # Inicio de la medida temporal; el tiempo de carga de pesos se mide por separado cuando corresponde.
    start = time.perf_counter()
    # Desactiva el seguimiento de gradientes: consultar el modelo no lo entrena.
    with torch.inference_mode():
        # Predice tokens nuevos con generación greedy y límite de 180 tokens fijados en GENERATION.
        # pad_token_id indica qué token usar como relleno; aquí, el de fin de texto.
        output = model.generate(
            **inputs, **GENERATION, pad_token_id=tokenizer.eos_token_id
        )
    # Espera a las operaciones MPS pendientes para que la medida temporal tenga límites definidos.
    if device == "mps":
        # Así la latencia incluye la generación completa en la GPU, no solo su encolado.
        torch.mps.synchronize()
    # output repite el prompt antes de la respuesta: [0, n:] toma la única fila desde el token n,
    # donde n es la longitud del prompt.
    tokens = output[0, inputs["input_ids"].shape[1] :]
    # Decodifica la salida y devuelve consumo/tiempo; coste local sigue desconocido porque no medimos energía/hardware.
    return {
        # Texto decodificado tal como lo generó el modelo, sin reparar.
        "respuesta_original": tokenizer.decode(tokens, skip_special_tokens=True),
        # Segundos de generación, sin contar la carga del modelo.
        "latencia_s": time.perf_counter() - start,
        # Tokens del prompt (system, few-shot si lo hay e incidencia).
        "tokens_entrada": inputs["input_ids"].shape[1],
        # Tokens nuevos generados por el modelo.
        "tokens_salida": len(tokens),
        # None = coste desconocido; ejecutar en local no significa coste cero.
        "coste_usd": None,
        "coste_metodo": "Sin tarifa API; hardware/energía no medidos",
        # cuda, mps o cpu: el dispositivo donde se generó.
        "hardware": device,
        # Identidad exacta del modelo y la revisión usados.
        "model": MODEL_ID,
        "revision": REVISION,
        # Parámetros de generación aplicados (greedy y límite de 180 tokens).
        "parametros": GENERATION,
        # La plantilla se aplicó sin razonamiento (thinking).
        "enable_thinking": False,
    }
