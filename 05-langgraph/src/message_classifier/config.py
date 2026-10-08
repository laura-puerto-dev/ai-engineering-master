MAX_ATTEMPTS = 3
SIMULATED_FAILURES = 0

COMPLAINT_MESSAGE = "Mi pedido lleva una semana de retraso y nadie me da una solución."
QUESTION_MESSAGE = "¿Cuánto tarda normalmente un envío?"

TEST_MESSAGE = COMPLAINT_MESSAGE

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
