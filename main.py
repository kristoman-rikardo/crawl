import asyncio
import re
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Funksjon for postprosessering av skrapet innhold, tilsvarende JavaScript-logikken
def process_content(side_innhold: str) -> str:
    if not side_innhold:
        return "feil"
    
    # 1) Splitt innholdet på linjeskift
    lines = side_innhold.splitlines()
    
    # 2) Definer liste med regex for støy
    skip_patterns = [
        re.compile(r"cookie", re.IGNORECASE),
        re.compile(r"policy", re.IGNORECASE),
        re.compile(r"cdn", re.IGNORECASE),
        re.compile(r"banner", re.IGNORECASE),
        re.compile(r"\.(jpg|jpeg|png|svg|gif)", re.IGNORECASE),
        re.compile(r"<script", re.IGNORECASE),
        re.compile(r"</script>", re.IGNORECASE),
        re.compile(r"privacy", re.IGNORECASE)
    ]
    
    # 3) Filtrer bort linjer som matcher støy
    filtered_lines = []
    for line in lines:
        if not any(pattern.search(line) for pattern in skip_patterns):
            filtered_lines.append(line)
    
    # 4) Fjern URL-lenker (http/https/www)
    cleaned_lines = [re.sub(r"https?:\/\/\S+|www\.\S+", "", line) for line in filtered_lines]
    
    # 5) Trim whitespace og fjern tomme linjer
    cleaned_lines = [line.strip() for line in cleaned_lines if line.strip()]
    
    # 6) Sett sammen resultatet
    product_info = "\n".join(cleaned_lines)
    return product_info

# Subklasse for blokkering av unødvendige ressurser og rask nettleserstart
class FastWebCrawler(AsyncWebCrawler):
    async def setup_browser(self):
        playwright = await async_playwright()
        self._browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def setup_page(self):
        page = await super().setup_page()
        await page.route("**/*", self._block_non_text_resources)
        return page

    async def _block_non_text_resources(self, route):
        if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
            await route.abort()
        else:
            await route.continue_()

app = FastAPI()
crawler = None

@app.on_event("startup")
async def startup_event():
    global crawler
    crawler = FastWebCrawler()
    await crawler.__aenter__()  # Starter ressursene (Playwright)

@app.on_event("shutdown")
async def shutdown_event():
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)
        crawler = None

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """
    Skraper siden med wait_until="domcontentloaded", bearbeider innholdet
    og returnerer det bearbeidede resultatet som 'productInfo'.
    """
    global crawler
    try:
        result = await crawler.arun(
            url=url,
            wait_until="domcontentloaded"
        )
        # Bearbeid det skrapede innholdet med process_content-funksjonen
        product_info = process_content(result.markdown)
        return {"content": product_info}
    except PlaywrightTimeoutError:
        # Hvis det oppstår en timeout, forsøker vi å hente delvis innhold
        page = crawler.page
        if not page:
            return {"error": "Timeout: Siden startet ikke å laste."}
        partial_html = await page.content()
        product_info = process_content(partial_html)
        return {"content": product_info}

