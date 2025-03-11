import asyncio
from fastapi import FastAPI, Query
from cachetools import LRUCache

# Crawl4AI:
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

app = FastAPI()

# Globale variabler
crawler = None
semaphore = None
cache = LRUCache(maxsize=50)  # Lagrer inntil 50 sider i minnet

@app.on_event("startup")
async def startup():
    """
    Starter én global nettleser (via AsyncWebCrawler) ved oppstart,
    slik at vi unngår å spinne opp nye browser-instanser på hver forespørsel.
    """
    global crawler, semaphore

    # Bygg en BrowserConfig som aktiverer headless modus,
    # kjører JavaScript, og setter f.eks. --no-sandbox-flagg til Chromium.
    browser_conf = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        launch_options={
            "args": ["--no-sandbox"]
        }
    )

    # Opprett og "åpne" crawleren permanent
    crawler = AsyncWebCrawler(config=browser_conf)
    await crawler.__aenter__()

    # Begrens antall samtidige requests
    semaphore = asyncio.Semaphore(10)

@app.on_event("shutdown")
async def shutdown():
    """
    Rydder opp ved server-stopp; lukker den globale crawleren hvis den kjører.
    """
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)
        crawler = None

@app.get("/")
def root():
    """
    Et enkelt 'helse'-endepunkt.
    """
    return {"status": "ok"}

@app.get("/crawl")
async def crawl_url(url: str = Query(..., title="URL to scrape")):
    """
    Rask scraping av gitt URL, returnert som Markdown.
    Bruker en global crawler for minimalt overhead.
    """
    # Sjekk om vi allerede har innholdet i vår minne-cache
    if url in cache:
        return {"content": cache[url]}

    # Begrens samtidighet via semafor
    async with semaphore:
        # Konfig som bare venter til DOMContentLoaded, har maks 3 sek timeout
        # og blokkerer unødvendige ressurser (bilder, fonter osv.)
        run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(),
            page_goto_kwargs={
                "wait_until": "domcontentloaded",
                "timeout": 3000
            },
            route_hook=_block_extras
        )

        try:
            # Utfør selve crawlingen
            result = await crawler.arun(url=url, config=run_conf)
            content = result.markdown.raw_markdown
        except Exception as e:
            # Returner feilmelding hvis noe går galt
            content = f"Feil under henting av '{url}': {str(e)}"

    # Legg resultat i cache for rask gjenbruk
    cache[url] = content
    return {"content": content}

async def _block_extras(route):
    """
    Blokkerer typer vi ikke trenger: bilder, fonter, stylesheets, video.
    Dette reduserer lastingstid betydelig.
    """
    req = route.request
    if req.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()
