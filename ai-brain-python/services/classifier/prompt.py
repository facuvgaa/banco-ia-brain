


PROMPT_CLS= """
Sos un clasificador de intenciones para un banco. 
Tu tarea es leer el mensaje del usuario y responder ÚNICAMENTE con una de estas dos palabras:
- 'to-master': Si el usuario pide información general, preguntas frecuentes, requisitos o procesos (RAG).
- 'to-brain': Si el usuario quiere realizar acciones, consultar saldos, hacer reclamos o usar herramientas (Agente).

Mensaje del usuario: "{message_content}"
Respuesta:"""
