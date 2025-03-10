import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Crawls the given URL and returns extracted content."""
    async with async_playwright() as p:
        # Start Playwright-nettleseren for dette kallet
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        # Bruk browser-objektet i AsyncWebCrawler
        async with AsyncWebCrawler(browser=browser) as crawler:
            result = await crawler.arun(url=url)
        # Lukk nettleseren eksplisitt (avsluttes også av 'async with', men for sikkerhet)
        await browser.close()
    return {"content": result.markdown}
