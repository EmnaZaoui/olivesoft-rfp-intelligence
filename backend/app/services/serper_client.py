import requests
from app.config import settings

SERPER_URL = "https://google.serper.dev/search"


def search_web(query: str, num_results: int = 5) -> list[dict]:
    headers = {"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return [{"title": "ERROR", "link": "", "snippet": f"Erreur Serper API: {e}"}]

    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in data.get("organic", [])[:num_results]
    ]