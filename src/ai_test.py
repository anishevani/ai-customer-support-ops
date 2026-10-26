"""One Responses API call. Proves this project can invoke a model."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = OpenAI()

response = client.responses.create(
    model=os.environ["OPENAI_MODEL"],
    input="Classify this support issue: I cannot log into my account.",
)

print(response.output_text)
if response.usage is not None:
    print(
        f"tokens input={response.usage.input_tokens} "
        f"output={response.usage.output_tokens}"
    )
