import re
from typing import Tuple

# Marcador al final de la respuesta del asistente cuando ofrece “¿algo más?”; el servicio lo quita y activa enrutado post-cierre.
POST_CLOSE_MARKER = "[POST_CLOSE]"
# TTL (seg) del flag en Redis: espera el siguiente mensaje del usuario.
POST_CLOSE_TTL_S = 900


def strip_post_close_marker(text: str) -> Tuple[str, bool]:
    """Quita [POST_CLOSE] y devuelve (texto limpio, True si tenía el marcador)."""
    if not text or POST_CLOSE_MARKER not in text:
        return (text or "").strip(), False
    clean = re.sub(
        r"\[POST_CLOSE\]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return clean, True
