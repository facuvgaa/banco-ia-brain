import os
import boto3
from langchain_aws import ChatBedrock
from dotenv import load_dotenv

load_dotenv()

def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )


def get_triangle_agent():
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
    )

def get_brain_agent():
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    )


