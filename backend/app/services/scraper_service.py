import requests
from bs4 import BeautifulSoup
import asyncio
import concurrent.futures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

MIN_ACCEPTABLE_LENGTH = 400

BLOCKING_MARKERS = [
    "just a moment", "checking your browser", "cloudflare",
    "enable javascript", "captcha", "access denied", "attention required",
]


def _looks_blocked_or_empty(text: str) -> bool:
    if not text or len(text) < MIN_ACCEPTABLE_LENGTH:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in BLOCKING_MARKERS)


def _clean_soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def _scrape_with_requests(url: str, timeout: int = 10) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"SCRAPE_ERROR: requests a échoué sur {url} ({e})"

    soup = BeautifulSoup(response.text, "html.parser")
    text = _clean_soup_text(soup)
    if not text:
        return f"SCRAPE_ERROR: page vide via requests ({url})"
    return text


async def _scrape_with_playwright_async(url: str, timeout_ms: int = 20000) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "SCRAPE_ERROR: playwright non installé"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=HEADERS["User-Agent"], locale="fr-FR")
            page = await context.new_page()
            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            html = await page.content()
            await browser.close()
    except Exception as e:
        return f"SCRAPE_ERROR: playwright a échoué sur {url} ({e})"

    soup = BeautifulSoup(html, "html.parser")
    text = _clean_soup_text(soup)
    if not text:
        return f"SCRAPE_ERROR: page vide via playwright ({url})"
    return text

def scrape_page_text(url: str, max_chars: int = 8000) -> str:
    text = _scrape_with_requests(url)

    if text.startswith("SCRAPE_ERROR") or _looks_blocked_or_empty(text):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(_scrape_with_playwright_async(url)))
                text = future.result(timeout=30)
        except Exception as e:
            text = f"SCRAPE_ERROR: playwright fallback échoué ({e})"

    if text.startswith("SCRAPE_ERROR"):
        return text
    return text[:max_chars]


def fetch_raw_html(url: str, timeout: int = 10) -> str:
    """Retourne le HTML brut (nécessaire pour extraire des liens depuis une page listing)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=HEADERS["User-Agent"])
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                html = page.content()
                browser.close()
                return html
        except Exception:
            return ""