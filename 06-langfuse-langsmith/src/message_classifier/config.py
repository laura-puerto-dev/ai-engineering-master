# LLM configuration
MODEL_NAME = "llama3.1"
MODEL_TEMPERATURE = 0

# Judge configuration
JUDGE_MODEL_NAME = "gpt-4.1-mini"
JUDGE_MODEL_TEMPERATURE = 0

# Classification and retry configuration
MAX_ATTEMPTS = 3
SIMULATED_FAILURES = 0

# Test messages
QUESTION_MESSAGE = "¿Cuánto tarda normalmente un envío?"
COMPLAINT_MESSAGE = "Mi pedido lleva una semana de retraso y nadie me da una solución."
TEST_MESSAGE = COMPLAINT_MESSAGE

# Observability
TRACE_NAME = "novashop-complaint"

# Business context
COMPANY_CONTEXT = """
Empresa ficticia: NovaShop, tienda de comercio electrónico.

Política de envíos:
- Los envíos nacionales tardan entre 2 y 4 días laborables.
- Los envíos internacionales tardan entre 5 y 10 días laborables.
- Los plazos comienzan desde la confirmación del pedido.

Gestión de incidencias:
- Las incidencias de entrega se gestionan a través del equipo de soporte.
- Para investigar una incidencia es necesario el número de pedido.
- El asistente no tiene acceso directo al estado de los pedidos.

Devoluciones:
- Los clientes pueden solicitar una devolución durante los 30 días
  posteriores a la recepción del pedido.
"""
