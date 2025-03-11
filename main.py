import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright

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
    Laster siden med wait_until="domcontentloaded" uten timeout.
    """
    global crawler
    result = await crawler.arun(
        url=url,
        wait_until="domcontentloaded"
    )
    return {"content": result.markdown}
