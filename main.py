import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from cachetools import LRUCache  # Hvis du også ønsker caching

app = FastAPI()

# Globale variabler for delt Playwright-instans, delt browser og semafor for samtidighet
playwright_instance = None
browser = None
semaphore = None
cache = LRUCache(maxsize=50)  # Valgfritt, for caching av de 50 mest brukte URL-ene

@app.on_event("startup")
async def startup_event():
    global playwright_instance, browser, semaphore
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(headless=True, args=["--no-sandbox"])
    semaphore = asyncio.Semaphore(10)  # Begrens til for eksempel 10 samtidige kall

@app.on_event("shutdown")
async def shutdown_event():
    global playwright_instance, browser
    if browser:
        await browser.close()
    if playwright_instance:
        await playwright_instance.stop()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Scrapes the given URL using a shared browser instance with concurrency control."""
    # Sjekk cache først (om caching er ønskelig)
    if url in cache:
        return {"content": cache[url]}
    
    async with semaphore:
        # Opprett en ny side for dette kallet
        page = await browser.new_page()
        try:
            # Send inn den delte browser-instansen og den nye siden til AsyncWebCrawler
            async with AsyncWebCrawler(browser=browser, page=page) as crawler:
                result = await crawler.arun(url=url)
                content = result.markdown
        finally:
            await page.close()
    
    # Legg til i cache hvis innholdet er gyldig (valgfritt)
    if content:
        cache[url] = content

    return {"content": content}
