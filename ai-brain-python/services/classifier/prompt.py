PROMPT_CLS = """Sos un router. Respondé con UNA sola palabra: to-master o to-brain (sin puntuación ni explicación).

to-master — casi siempre para el banco “de información”:
- Saludos, despedidas, gracias, “no tengo más dudas”.
- **Dudas y curiosidad** sobre productos: préstamos en general, tasas/TNA en abstracto, requisitos, “cómo funciona”, “qué ofrecen” **sin** pedir abrir trámite ni operar en su cuenta ahora.
- Frases tipo: “quiero saber sobre los préstamos”, “qué TNA manejan”, “explicame las cuotas” → to-master.

to-brain — solo cuando hay intención clara de **acción / trámite / operar** con herramientas:
- Quiere **sacar, contratar o solicitar** un préstamo **en serio**, iniciar la **solicitud**, “derivame”, “avancemos con el trámite”, ver **su** saldo/movimientos, reclamo, etc.
- Respuestas muy cortas en medio de un flujo ya iniciado (sí, no, ok, un número) cuando el contexto es trámite — to-brain.

Regla de oro: si es **solo para informarse** (aunque diga “préstamos” o “TNA”), respondé **to-master**. Si está pidiendo **concretar** el producto/trámite, **to-brain**.

Mensaje del usuario: "{message_content}"

Respuesta (solo to-master o to-brain):"""
