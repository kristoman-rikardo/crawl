import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# 1) Subklasse for blokkering av unødvendige ressurser
class FastWebCrawler(AsyncWebCrawler):
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
    # 2) Bruk subklassen
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
    Forsøker å laste siden med 1,5 sek timeout.
    Hvis tiden overskrides, prøver vi å returnere 'delvis' innhold likevel.
    """
    global crawler
    try:
        result = await crawler.arun(
            url=url,
            wait_until="networkidle",
            goto_options={"timeout": 1}  # 1,5 sekunder
        )
        return {"content": result.markdown}
    except PlaywrightTimeoutError:
        page = crawler.page  
        if not page:
            return {"error": "Timeout før siden begynte å laste."}
        partial_html = await page.content()
        return {
            "content": partial_html,
            "warning": "Timeout: returnerer ufullstendig innhold"
        }
