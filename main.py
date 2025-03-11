import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

app = FastAPI()
crawler = None

@app.on_event("startup")
async def startup_event():
    global crawler
    crawler = AsyncWebCrawler()
    await crawler.__aenter__()  # Start ressursene (Playwright)

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
            wait_until="domcontentloaded",
            goto_options={"timeout": 1500}  # 1,5 sekunder
        )
        return {"content": result.markdown}
    except PlaywrightTimeoutError:
        # Siden ble ikke helt ferdig lastet før timeout
        # Forsøk å hente ut *det som eventuelt rakk å laste*:
        page = crawler.page  # Normalt referanse til siste brukte Playwright-side

        if not page:
            # Hvis 'page' er None, har vi ikke noe delvis innhold å hente
            return {"error": "Timeout før siden begynte å laste."}

        # Hent innholdet så langt
        partial_html = await page.content()
        # Evt. kjøre litt ekstra parse for markdown
        # men 'crawler.parse_to_markdown' er vanligvis privat
        # Her kan du bygge et eget "konverter HTML til markdown" hvis du vil
        return {
            "content": partial_html, 
            "warning": "Timeout: returnerer ufullstendig innhold"
        }
