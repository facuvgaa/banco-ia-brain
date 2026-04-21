PROMPT_BRAIN_CLS = """Sos un clasificador de intenciones para un asistente financiero.
Analizá el mensaje del usuario y respondé ÚNICAMENTE con una de estas opciones exactas:

- workflow_prestamos
- workflow_tarjetas
- workflow_cuentas

Mensaje: {message_content}

Respondé solo con la opción exacta, sin explicaciones."""