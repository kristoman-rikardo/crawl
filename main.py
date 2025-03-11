import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler

app = FastAPI()

# Oppretter en global crawler-variabel
crawler = None

@app.on_event("startup")
async def startup_event():
    """
    Kalles kun én gang når FastAPI-applikasjonen starter opp.
    Vi oppretter én global crawler-instans og åpner den (inkl. Playwright-browser).
    """
    global crawler
    crawler = AsyncWebCrawler()
    await crawler.__aenter__()  # Start ressursene i crawleren

@app.on_event("shutdown")
async def shutdown_event():
    """
    Kalles når applikasjonen stenges (for eksempel ved stans eller deploy-oppdatering).
    Vi lukker den globale crawler-instansen her.
    """
    global crawler
    if crawler:
        await crawler.__aexit__(None, None, None)
        crawler = None

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """
    Henter innhold fra gitt URL ved å bruke den allerede åpne crawler-instansen.
    """
    global crawler
    result = await crawler.arun(url=url)
    return {"content": result.markdown}
