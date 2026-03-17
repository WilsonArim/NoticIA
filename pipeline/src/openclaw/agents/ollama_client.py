"""
Cliente Ollama Cloud — compatível com API OpenAI.
Usado por todos os agentes do NoticIA.
"""
import os
import json
import time
import logging
from typing import Any, Callable, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")


def get_client() -> OpenAI:
    return OpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key=OLLAMA_API_KEY,
    )


def chat(
    model: str,
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """Chama o modelo e devolve o texto da resposta. Faz retry em caso de erro."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("Ollama attempt %d/%d failed: %s", attempt + 1, retries, e)
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                raise


def chat_with_tools(
    model: str,
    system: str,
    user: str,
    tools: list[dict],
    tool_executor: Callable[[str, dict], dict],
    max_rounds: int = 5,
) -> str:
    """
    Loop completo de tool calling:
    1. Envia mensagem ao modelo
    2. Se o modelo pede tool call, executa a tool
    3. Envia resultado de volta
    4. Repete até o modelo devolver resposta final
    """
    client = get_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=4096,
        )
        choice = response.choices[0]

        # Modelo quer chamar uma tool
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)  # type: ignore[arg-type]
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                logger.info("Tool call: %s(%s)", tool_name, tool_args)

                tool_result = tool_executor(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                })
        else:
            # Resposta final
            return choice.message.content or ""

    return "Erro: máximo de rounds de tool calling atingido"
