import mesa
import requests
from bs4 import BeautifulSoup
from db_setup import Opportunity, Session


class AgentPostdocScraper(mesa.Agent):
    """Collects postdoc and visiting professor positions from research institute pages."""

    SOURCES = [
        {
            "name": "ISTA Postdoc Office",
            "url": "https://postdoc.pages.ist.ac.at/scientific-visitors-with-phd/",
            "keywords": ["postdoc", "fellow", "visiting", "scientist", "professor", "researcher"],
            "location": "Austria",
        },
        {
            "name": "Google Research – Visiting Researcher",
            "url": "https://research.google/programs-and-events/visiting-researcher-program/",
            "keywords": ["visiting", "researcher", "postdoc", "faculty", "program", "collaborate"],
            "location": "Global",
        },
        {
            "name": "Katina Magazine – Research Ecosystem",
            "url": "https://katinamagazine.org/content/article/resource-reviews/2024/can-the-worlds-research-ecosystem-be-openly-indexed",
            "keywords": ["research", "postdoc", "academic", "scholar", "scientist", "open"],
            "location": "Global",
        },
    ]

    def __init__(self, unique_id, model, limit=10):
        super().__init__(unique_id, model)
        self.limit = limit

    def step(self):
        print(f"[Agent-{self.unique_id}] AgentPostdocScraper starting ({len(self.SOURCES)} sources)...")
        total = 0
        for src in self.SOURCES:
            count = self._scrape_page(src)
            total += count
        print(f"[Agent-{self.unique_id}] AgentPostdocScraper finished — {total} items ingested.")

    def _scrape_page(self, src):
        url = src["url"]
        name = src["name"]
        keywords = src["keywords"]
        location = src.get("location", "")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        count = 0
        try:
            page = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(page.text, "html.parser")
            session = Session()

            for el in soup.find_all(["p", "li", "h2", "h3", "h4"]):
                if count >= self.limit:
                    break
                text = el.get_text(strip=True)
                if len(text) < 10:
                    continue
                if any(kw in text.lower() for kw in keywords):
                    a_tag = el.find("a")
                    link = a_tag.get("href", url) if a_tag else url
                    if link and not link.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        link = f"{parsed.scheme}://{parsed.netloc}{link}" if link.startswith("/") else url

                    # Build a descriptive title from the source name
                    short_text = text[:80].replace("\n", " ")
                    session.add(Opportunity(
                        type="postdoc_visiting",
                        title=f"{name} – {short_text}",
                        description=text[:500],
                        source=name,
                        location=location,
                        url=link,
                    ))
                    count += 1

            session.commit()
            session.close()
            print(f"  [{name}] -> {count} items")
        except Exception as e:
            print(f"  [{name}] Error: {e}")
        return count
