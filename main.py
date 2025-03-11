import asyncio
from fastapi import FastAPI, Query
from cachetools import LRUCache

# Grunnleggende Crawl4AI-imports
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    CacheMode
)

app = FastAPI()

# Global crawler (startes bare én gang) + semafor + en liten LRUCache
crawler = None
semaphore = None
cache = LRUCache(maxsize=50)

@app.on_event("startup")
async def startup_event():
    """
    Starter én global async crawler, slik at vi
    slipper å spinne opp ny nettleser for hver request.
    """
    global crawler, semaphore

    # Ingen spesielle BrowserConfig-argumenter som kan krasje.
    crawler = AsyncWebCrawler()
    await crawler.__aenter__()  # 'Åpner' crawleren permanent

    # Tillat for eksempel 10 samtidige kall
    semaphore = asyncio.Semaphore(10)

@app.on_event("shutdown")
async def shutdown_event():
    """
    Rydder opp når serveren stopper.
    Lukker crawleren hvis den kjører.
    """
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)
        crawler = None

@app.get("/crawl")
async def crawl_url(url: str = Query(..., title="URL to scrape")):
    """
    Henter innhold fra en URL, konverterer til Markdown og returnerer.
    Holder én global crawler for rask oppstart.
    """
    # Hvis vi har innholdet i cache, returnér raskt
    if url in cache:
        return {"content": cache[url]}

    async with semaphore:
        # Bygg en run-konfig som:
        # - Bypasser eventuell http-cache (frisk henting hver gang)
        # - Kun venter til "domcontentloaded" og har timeout på 3 sek
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_goto_kwargs={
                "wait_until": "domcontentloaded",
                "timeout": 3000
            },
        )
        try:
            result = await crawler.arun(url=url, config=config)
            # Hent ut ren Markdown
            content = result.markdown.raw_markdown
        except Exception as e:
            content = f"Feil under henting av '{url}': {str(e)}"

    # Legg til i minnecache før vi returnerer
    cache[url] = content
    return {"content": content}
