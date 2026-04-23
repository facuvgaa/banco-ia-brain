"""
Test de idoneidad (estilo CNV) — 9 ítems. Las opciones suman “puntos de apetito de riesgo”.
Perfil: CONSERVADOR | MODERADO | ARRIESGADO (umbrales sobre score total 0..max).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Cada letra aporta riesgo_score (0 = más conservador, 3 = más arriesgado en 4-opción).
# P7 solo tiene 3 opciones.


@dataclass(frozen=True)
class QuizItem:
    id: int
    text: str
    # options: letra -> (texto, risk_score 0-3)
    options: List[Tuple[str, str, int]]


QUIZ: List[QuizItem] = [
    QuizItem(
        1,
        "Tu edad se encuentra dentro del rango de:",
        [
            ("A", "Menos de 25 años.", 3),
            ("B", "De 25 a 35 años.", 2),
            ("C", "De 36 a 55 años.", 1),
            ("D", "De 56 años o más.", 0),
        ],
    ),
    QuizItem(
        2,
        "¿Cuánto conocés del Mercado de Capitales (Acciones, Bonos, ON, Lecap, FCI, CEDEAR)?",
        [
            ("A", "No poseo conocimiento.", 0),
            (
                "B",
                "Tengo conocimientos básicos acerca de las distintas alternativas de inversión.",
                1,
            ),
            (
                "C",
                "Tengo conocimientos acerca del riesgo y rentabilidad potencial de los distintos instrumentos financieros.",
                2,
            ),
            (
                "D",
                "Poseo un profundo conocimiento (Profesional en Finanzas).",
                3,
            ),
        ],
    ),
    QuizItem(
        3,
        "¿Qué experiencia tenés como inversionista?",
        [
            ("A", "Ninguna.", 0),
            ("B", "Baja.", 1),
            ("C", "Media.", 2),
            ("D", "Alta.", 3),
        ],
    ),
    QuizItem(
        4,
        "¿Aproximadamente, qué porcentaje de tus ingresos mensuales ahorrás por mes?",
        [
            ("A", "Menos del 5%.", 0),
            ("B", "Entre el 5% y el 20%.", 1),
            ("C", "Entre el 21% y el 50%.", 2),
            ("D", "Más del 50%.", 3),
        ],
    ),
    QuizItem(
        5,
        "¿Qué porcentaje de tus ahorros estás dispuesto a destinar a inversiones en el Mercado de Capitales?",
        [
            ("A", "Menos del 25%.", 0),
            ("B", "Entre el 25% y el 40%.", 1),
            ("C", "Entre el 41% y el 65%.", 2),
            ("D", "Más del 65%.", 3),
        ],
    ),
    QuizItem(
        6,
        "¿Cuánto tiempo conservarías esta inversión?",
        [
            ("A", "Menos de 180 días.", 0),
            ("B", "Entre 180 días y 1 año.", 1),
            ("C", "De 1 a 2 años.", 2),
            ("D", "Más de 2 años.", 3),
        ],
    ),
    QuizItem(
        7,
        "En el momento de realizar una inversión, ¿cuál de las siguientes opciones preferís?",
        [
            (
                "A",
                "Preservar el dinero invertido con una rentabilidad mínima.",
                0,
            ),
            (
                "B",
                "Ganancia apenas superior a un plazo fijo, aunque con variación mínima del mercado.",
                1,
            ),
            (
                "C",
                "Obtener una ganancia significativa, aceptando riesgo de perder más de la mitad del capital.",
                2,
            ),
        ],
    ),
    QuizItem(
        8,
        "¿Qué porcentaje de disminución del capital de tus inversiones/ahorros estarías dispuesto a asumir? (Cifras orientativas, no aseguran pérdida.)",
        [
            ("A", "Entre 0% y el 5%.", 0),
            ("B", "Entre el 5% y el 15%.", 1),
            ("C", "Entre el 15% y el 30%.", 2),
            ("D", "Más del 30%.", 3),
        ],
    ),
    QuizItem(
        9,
        "Si tu inversión se desvaloriza 15% a tan solo un mes de haberla adquirido, ¿cómo procederías?",
        [
            ("A", "Vendería la inversión para evitar una mayor pérdida.", 0),
            ("B", "Transferiría activos a inversiones de menor riesgo.", 1),
            ("C", "Esperaría que recupere su valor inicial.", 2),
            (
                "D",
                "Compraría más aprovechando el menor precio actual.",
                3,
            ),
        ],
    ),
]


def max_quiz_score() -> int:
    return sum(max(o[2] for o in it.options) for it in QUIZ)


def _score_for(letter: str, item: QuizItem) -> int:
    u = (letter or "").strip().upper()[:1]
    for L, _txt, sc in item.options:
        if L == u:
            return sc
    return 0


def parse_quiz_letter(
    user_text: str, item: Optional[QuizItem] = None
) -> str:
    """Acepta 'A', 'a', 'opción b', 'la B', '2' para la segunda opción, etc."""
    t = (user_text or "").strip()
    if not t:
        return "A"
    m = re.search(r"^\s*([ABCDabcd])\b", t)
    if m:
        return m.group(1).upper()
    m = re.search(r"\bopcion\s*([ABCDabcd])", t, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"^\s*([1-4])\b", t)
    if m and item:
        n = int(m.group(1))
        opts = [o[0] for o in item.options]
        if 1 <= n <= len(opts):
            return opts[n - 1]
    # última heurística: primera letra A-D
    m = re.search(r"([ABCD])", t.upper())
    if m:
        return m.group(1)
    if item:
        nopt = len(item.options)
        if nopt == 3:
            for low, ch in (("tercera", "C"), ("segunda", "B"), ("primera", "A")):
                if low in t.lower():
                    return ch
    return "A"


def compute_profile(answers: List[str]) -> Tuple[str, int, int, str]:
    """
    answers: 9 letras, índice alineado con QUIZ.
    Retorna: (tier CONSERVADOR|MODERADO|ARRIESGADO, total_score, max_loss_percent, horizon_code)
    """
    if len(answers) != len(QUIZ):
        raise ValueError("Se esperan 9 respuestas")
    total = 0
    for letter, it in zip(answers, QUIZ):
        total += _score_for(letter, it)

    mx = max_quiz_score()
    # terciles en el rango 0..mx
    t1 = mx / 3.0
    t2 = 2 * mx / 3.0
    if total <= t1:
        tier = "CONSERVADOR"
    elif total <= t2:
        tier = "MODERADO"
    else:
        tier = "ARRIESGADO"

    # max pérdida asumible (Q8, índice 7) → entero al % alto del rango
    q8 = QUIZ[7]
    l8 = parse_quiz_letter(answers[7], q8)
    loss_map = {"A": 5, "B": 15, "C": 30, "D": 35}
    max_loss = loss_map.get(l8, 15)

    # horizonte (Q6) → string corto para DTO
    hmap = {
        "A": "<180d",
        "B": "180d-1a",
        "C": "1-2a",
        "D": ">2a",
    }
    h6 = parse_quiz_letter(answers[5], QUIZ[5])
    horizon = hmap.get(h6, "180d-1a")

    return tier, int(total), max_loss, horizon


def format_question_block(item: QuizItem) -> str:
    lines = [f"**Pregunta {item.id}/9**", "", item.text, ""]
    for L, txt, _ in item.options:
        lines.append(f"**{L})** {txt}")
    lines.append("")
    opts = [o[0] for o in item.options]
    if len(opts) == 3:
        lines.append("Respondé con la letra (A, B o C).")
    else:
        lines.append("Respondé con la letra (A, B, C o D según corresponda).")
    return "\n".join(lines)
