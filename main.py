import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from cachetools import LRUCache  # For caching

app = FastAPI()

# Globale variabler for delt Playwright-instans, delt browser, semafor og cache
playwright_instance = None
browser = None
semaphore = None
cache = LRUCache(maxsize=50)  # Lagrer de 50 mest brukte URL-ene

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
    """Scrapes the given URL using a shared browser instance with concurrency control,
    optimalisert med raskere sideinnlasting og blokkering av unødvendige ressurser."""
    
    # Sjekk cache først
    if url in cache:
        return {"content": cache[url]}
    
    async with semaphore:
        # Opprett en ny side for dette kallet
        page = await browser.new_page()
        
        # Definer en funksjon for å blokkere unødvendige ressurser
        async def block_resources(route):
            if route.request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()
        
        try:
            # Sett opp route for å blokkere spesifikke ressurser
            await page.route("**/*", block_resources)
            # Bruk "domcontentloaded" for raskere innlasting
            await page.goto(url, wait_until="load")
            
            # Bruk AsyncWebCrawler med den delte browser-instansen og den konfigurerte siden
            async with AsyncWebCrawler(browser=browser, page=page) as crawler:
                result = await crawler.arun(url=url)
                content = result.markdown
        finally:
            await page.close()
    
    # Cache resultatet dersom det er gyldig
    if content:
        cache[url] = content

    return {"content": content}
