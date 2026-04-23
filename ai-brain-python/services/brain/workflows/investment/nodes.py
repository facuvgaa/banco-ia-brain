import logging
from functools import partial

from langchain_core.messages import SystemMessage
from langgraph.types import interrupt
from services.brain.workflows.investment.state import InvestmentState
from services.brain.workflows.investment.questionnaire import (
    QUIZ,
    compute_profile,
    format_question_block,
    parse_quiz_letter,
)
from services.brain.workflows.investment.tools import (
    fetch_profile_investor,
    save_profile_investor,
)
from services.brain.workflows.investment.prompt import (
    SYSTEM_INVESTMENT_ADVISOR,
    tier_blurb,
)

logger = logging.getLogger(__name__)

INTRO_QUIZ = (
    "Hola, soy el asesor de inversiones del Banco Moustro. **No tenés aún un perfil de inversor registrado** "
    "(idoneidad / CNV) para este cliente, así que primero hacemos el test obligatorio. "
    "Son **9 preguntas**; en cada una respondé con la letra **A, B, C o D** (o lo que indique el enunciado).\n\n"
)


def _cleared_quiz_state() -> dict:
    return {
        "quiz_answers": [],
        "investor_tier": None,
        "quiz_total_score": None,
        "max_loss_percent": None,
        "horizon": None,
        "profile_persisted": False,
    }


def check_profile_node(state: InvestmentState) -> dict:
    """
    La API manda. Si en GET no hay perfil (hasProfile + riskLevel), va el test, aunque el
    checkpoint de Redis tenga un cuestionario viejo “completo” (sino borrás en DB y el grafo
    te seguía mandando al asesor con estado fantasma).
    Con perfil en API → asesor. Cuestionario a mitad sin perfil en API → seguir.
    """
    answers = list(state.get("quiz_answers") or [])

    try:
        data = fetch_profile_investor(state["customer_id"])
    except Exception as e:
        logger.warning("[investment] GET profile: %s — se hace el test", e)
        if len(answers) >= len(QUIZ):
            return {"has_profile": False, "messages": [], **_cleared_quiz_state()}
        return {"has_profile": False, "messages": []}

    hp = data.get("hasProfile")
    if hp is None:
        hp = data.get("has_profile")
    risk = data.get("riskLevel") if data.get("riskLevel") is not None else data.get("risk_level")
    tier_str = str(risk).strip() if risk is not None else ""
    has_api = hp is True and bool(tier_str)

    if not has_api:
        if len(answers) >= len(QUIZ):
            return {"has_profile": False, **_cleared_quiz_state()}
        if 0 < len(answers) < len(QUIZ):
            return {"has_profile": False}
        return {"has_profile": False}

    if 0 < len(answers) < len(QUIZ):
        mlp_raw = data.get("maxLossPercent")
        return {
            "has_profile": True,
            "investor_tier": tier_str.upper(),
            "max_loss_percent": int(mlp_raw) if mlp_raw is not None else 15,
            "horizon": data.get("horizon") or "180d-1a",
            "quiz_answers": [],
        }

    mlp = data.get("maxLossPercent")
    return {
        "has_profile": True,
        "investor_tier": tier_str.upper(),
        "max_loss_percent": int(mlp) if mlp is not None else 15,
        "horizon": data.get("horizon") or "180d-1a",
    }


def quiz_node(state: InvestmentState) -> dict:
    answers = list(state.get("quiz_answers") or [])
    n = len(answers)
    if n >= len(QUIZ):
        return {}
    item = QUIZ[n]
    block = format_question_block(item)
    if n == 0:
        text = INTRO_QUIZ + block
    else:
        text = block

    raw = interrupt(text)
    letter = parse_quiz_letter(str(raw) if raw is not None else "", item)
    new_ans = answers + [letter]
    if len(new_ans) < len(QUIZ):
        return {"quiz_answers": new_ans}
    tier, tot, mloss, horiz = compute_profile(new_ans)
    return {
        "quiz_answers": new_ans,
        "investor_tier": tier,
        "quiz_total_score": tot,
        "max_loss_percent": mloss,
        "horizon": horiz,
    }


def persist_profile_node(state: InvestmentState) -> dict:
    cid = state["customer_id"]
    tier = (state.get("investor_tier") or "MODERADO").upper()
    mloss = int(state.get("max_loss_percent") or 15)
    horiz = state.get("horizon") or "180d-1a"
    try:
        save_profile_investor(
            customer_id=cid,
            risk_level=tier,
            has_profile=True,
            max_loss_percent=mloss,
            horizon=horiz,
        )
    except Exception as e:
        logger.exception("[investment] guardar perfil: %s", e)
    return {"profile_persisted": True}


def advisor_node(state: InvestmentState, model) -> dict:
    tier = (state.get("investor_tier") or "MODERADO").upper()
    mloss = state.get("max_loss_percent")
    if mloss is None:
        mloss = 15
    horiz = state.get("horizon") or "180d-1a"
    perfil = tier_blurb(tier)
    sys_text = SYSTEM_INVESTMENT_ADVISOR.format(
        customer_id=state["customer_id"],
        tier=tier,
        max_loss=mloss,
        horizon=horiz,
        perfil_breve=perfil,
    )
    if state.get("quiz_total_score") is not None:
        from services.brain.workflows.investment.questionnaire import max_quiz_score

        sys_text += (
            f"\n\nEl usuario **acaba de completar** el test: perfil **{tier}**, "
            f"puntuación bruta {state['quiz_total_score']}/"
            f"{max_quiz_score()} (orientativa). Agradecé la paciencia y"
            f" ofrecé una primera orientación alineada al perfil."
        )
    messages = [SystemMessage(content=sys_text)] + list(state["messages"])
    res = model.invoke(messages)
    return {"messages": [res]}


def build_advisor_fn(model):
    return partial(advisor_node, model=model)
