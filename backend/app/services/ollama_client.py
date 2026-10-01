import json
import ollama
from app.config import settings

_client = ollama.Client(host=settings.ollama_host)

MAX_JSON_RETRIES = 3


def _try_parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            return json.loads(content[start:end + 1])
        raise


def chat_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Appelle le LLM en forçant du JSON. Retente automatiquement si la sortie
    n'est pas un JSON valide (edge case fréquent avec les modèles locaux).
    """
    last_error = None
    for attempt in range(1, MAX_JSON_RETRIES + 1):
        prompt = user_prompt
        if attempt > 1:
            prompt += (
                "\n\nIMPORTANT: ta dernière réponse n'était pas un JSON valide. "
                "Retourne UNIQUEMENT le JSON demandé, sans aucun texte avant ou après."
            )

        response = _client.chat(
            model=settings.ollama_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={"temperature": 0.1},
        )
        content = response["message"]["content"]
        try:
            return _try_parse_json(content)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            continue

    raise ValueError(f"JSON invalide après {MAX_JSON_RETRIES} tentatives: {last_error}")


def chat_text(system_prompt: str, user_prompt: str) -> str:
    response = _client.chat(
        model=settings.ollama_chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.5},
    )
    return response["message"]["content"]


def embed_text(text: str) -> list[float]:
    response = _client.embeddings(model=settings.ollama_embed_model, prompt=text)
    return response["embedding"]