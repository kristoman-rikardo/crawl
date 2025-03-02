import asyncio
from fastapi import FastAPI, Query
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright

app = FastAPI()

# Automatisk installasjon av Playwright-browsere
async def install_playwright():
    async with async_playwright() as p:
        await p.chromium.launch()

@app.on_event("startup")
async def startup_event():
    await install_playwright()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Crawls the given URL and returns extracted content."""
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {"content": result.markdown}
