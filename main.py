from fastapi import FastAPI, Query
import asyncio
from crawl4ai import AsyncWebCrawler

app = FastAPI()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Crawls the given URL and returns extracted content."""
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return {"content": result.markdown}
