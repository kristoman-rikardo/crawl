import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from cachetools import LRUCache

app = FastAPI()

# Globale variabler for delt Playwright-instans, browser, semafor og cache
playwright_instance = None
browser = None
semaphore = None
cache = LRUCache(maxsize=50)  # Cache for de 50 mest brukte URL-ene

@app.on_event("startup")
async def startup_event():
    global playwright_instance, browser, semaphore
    # Start Playwright og lanser browseren kun én gang
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(headless=True, args=["--no-sandbox"])
    # Sett opp semafor for å begrense samtidige kall (f.eks. 10 samtidige kall)
    semaphore = asyncio.Semaphore(10)

@app.on_event("shutdown")
async def shutdown_event():
    global playwright_instance, browser
    if browser:
        await browser.close()
    if playwright_instance:
        await playwright_instance.stop()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Scraper den oppgitte URL-en ved hjelp av en delt browser-instans, med caching og samtidighetsbegrensning."""
    # Sjekk om URL-en allerede er cachet
    if url in cache:
        return {"content": cache[url]}
    
    async with semaphore:
        page = await browser.new_page()
        try:
            # Bruk AsyncWebCrawler med den delte browseren og den nye siden
            async with AsyncWebCrawler(browser=browser, page=page) as crawler:
                result = await crawler.arun(url=url)
                content = result.markdown
        finally:
            await page.close()  # Sørg for å lukke siden for å frigjøre ressurser
    
    # Legg til resultatet i cachen dersom det er gyldig (ikke tomt)
    if content:
        cache[url] = content
    
    return {"content": content}
