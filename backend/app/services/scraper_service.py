import io
from concurrent.futures import ThreadPoolExecutor

import pdfplumber
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

MIN_ACCEPTABLE_LENGTH = 400
MAX_PDF_PAGES = 15

BLOCKING_MARKERS = [
    "just a moment", "checking your browser", "enable javascript",
    "captcha", "access denied", "attention required",
]


def _looks_blocked_or_empty(text: str) -> bool:
    if not text or len(text) < MIN_ACCEPTABLE_LENGTH:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in BLOCKING_MARKERS)


def _clean_soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "form", "aside"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def _pdf_bytes_to_text(content: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages[:MAX_PDF_PAGES]:
            t = page.extract_text()
            if t:
                parts.append(t)
    return " ".join("\n".join(parts).split())


def _scrape_with_requests(url: str, timeout: int = 12) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"SCRAPE_ERROR: requests a échoué sur {url} ({e})"

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
        try:
            text = _pdf_bytes_to_text(response.content)
        except Exception as e:
            return f"SCRAPE_ERROR: PDF illisible ({e})"
        return text or f"SCRAPE_ERROR: PDF sans texte ({url})"

    soup = BeautifulSoup(response.text, "html.parser")
    text = _clean_soup_text(soup)
    return text or f"SCRAPE_ERROR: page vide via requests ({url})"


def _scrape_with_playwright(url: str, timeout_ms: int = 20000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "SCRAPE_ERROR: playwright non installé"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"], locale="fr-FR")
            page = context.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            html = page.content()
            browser.close()
    except Exception as e:
        return f"SCRAPE_ERROR: playwright a échoué sur {url} ({e})"

    text = _clean_soup_text(BeautifulSoup(html, "html.parser"))
    return text or f"SCRAPE_ERROR: page vide via playwright ({url})"


def scrape_page_text(url: str, max_chars: int = 9000) -> str:
    """requests (HTML ou PDF) -> fallback Playwright si bloqué/vide."""
    text = _scrape_with_requests(url)
    is_pdf = url.lower().split("?")[0].endswith(".pdf")

    if not is_pdf and (text.startswith("SCRAPE_ERROR") or _looks_blocked_or_empty(text)):
        text = _scrape_with_playwright(url)

    if text.startswith("SCRAPE_ERROR"):
        return text
    return text[:max_chars]


def scrape_many(urls: list[str], max_workers: int = 4) -> dict[str, str]:
    """Scraping parallèle: le goulot d'étranglement est le réseau, pas le CPU."""
    results: dict[str, str] = {}
    if not urls:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_page_text, u): u for u in urls}
        for future, url in futures.items():
            try:
                results[url] = future.result()
            except Exception as e:
                results[url] = f"SCRAPE_ERROR: {e}"
    return results


def fetch_raw_html(url: str, timeout: int = 12) -> str:
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