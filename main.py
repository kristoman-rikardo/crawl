import asyncio
from fastapi import FastAPI, Query
from cachetools import LRUCache

# Crawl4AI-relaterte imports
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI()

crawler = None
semaphore = None
cache = LRUCache(maxsize=50)

@app.on_event("startup")
async def startup_event():
    """
    Oppretter én global (asynkron) crawler.
    Da slipper vi å spinne opp en ny nettleser for hver request.
    """
    global crawler, semaphore

    # Prøv "launch_args" for å sende inn egne Chromium-flags.
    # (Hvis "launch_args" ikke virker, prøv "playwright_browser_args")
    browser_conf = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        launch_args=["--no-sandbox"]
    )

    # Opprett en AsyncWebCrawler med gitt config
    crawler = AsyncWebCrawler(config=browser_conf)
    await crawler.__aenter__()  # Start crawleren permanent

    # Begrens antall samtidige kall
    semaphore = asyncio.Semaphore(10)

@app.on_event("shutdown")
async def shutdown_event():
    """
    Lukk crawler og rydd opp når appen stopper.
    """
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)
        crawler = None

@app.get("/crawl")
async def crawl_url(url: str = Query(..., title="URL å hente")):
    """
    Rask scraping av URL, returnert som Markdown.
    Cacher resultat for å unngå gjentatt lasting av samme side.
    """
    # Sjekk først om vi har det i cache
    if url in cache:
        return {"content": cache[url]}

    async with semaphore:
        # Bygg en run-konfig for "domcontentloaded" og maks 3 sek ventetid
        run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Henter alltid nytt
            markdown_generator=DefaultMarkdownGenerator(),
            page_goto_kwargs={
                "wait_until": "domcontentloaded",
                "timeout": 3000
            },
            route_hook=_block_extras  # Blokker bilder/font osv.
        )

        try:
            result = await crawler.arun(url=url, config=run_conf)
            content = result.markdown.raw_markdown
        except Exception as e:
            content = f"Feil under henting av '{url}': {str(e)}"

    # Lagre i cache
    if content:
        cache[url] = content

    return {"content": content}

async def _block_extras(route):
    """
    Blokkerer bilder, video, fonter og stylesheets for raskere innlasting.
    """
    req = route.request
    if req.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()
