from services.brain.classifier.prompt import PROMPT_BRAIN_CLS
from services.llms.models import get_bedrock_model_master
import logging


model = get_bedrock_model_master()

logger = logging.getLogger(__name__)

VALID_WORKFLOWS = ["workflow_loans", "workflow_tarjetas", "workflow_cuentas"]


def get_brain_classification(message_content):

    formatted_prompt = PROMPT_BRAIN_CLS.format(message_content=message_content)

    try:
        response = model.invoke(formatted_prompt)
        intent = response.content.strip().lower()
        logger.info(f"[BRAIN-CLS] Haiku decidió -> {intent}")
        return intent if intent in VALID_WORKFLOWS else "workflow_loans"

    except Exception as e:
        logger.error(f"Error en la clasificacion brain: {e}")
        return "workflow_loans"


