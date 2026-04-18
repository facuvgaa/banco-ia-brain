from prompt import PROMPT_CLS
from llms.models import get_bedrock_model_master
import logging

model = get_bedrock_model_master()

logger = logging.getLogger(__name__)

def get_classification(message_content):

    formatted_prompt = PROMPT_CLS.format(message_content=message_content)

    try:
        
        response = model.invoke(formatted_prompt)
        
        
        intent = response.content.strip().lower()
        

        logger.info(f"[DEBUG]:Haiku decidió -> {intent}")
        return intent if intent in ['to-master', 'to-brain'] else 'to-brain'
        
    except Exception as e:
        print(f"Error en clasificación con Bedrock: {e}")
        return "to-brain"