from fastapi import FastAPI, Query
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

@app.get("/crawl")
async def crawl(url: str = Query(..., title="URL to scrape")):
    """Crawls the given URL using httpx and BeautifulSoup."""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    
    if response.status_code != 200:
        return {"error": f"Failed to fetch URL, status code {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")
    return {"content": soup.get_text()[:2000]}  # Begrens til 2000 tegn for å unngå for store svar
