import mesa
import requests
from bs4 import BeautifulSoup
from db_setup import Opportunity, Session


class AgentInternshipScraper(mesa.Agent):
    """Collects internships from multiple sources referenced in the project resources."""

    # All URLs from the markdown mapped to Internships
    SOURCES = [
        {
            "name": "GitHub – Competitions-and-Programs-List",
            "url": "https://github.com/avinash201199/Competitions-and-Programs-List/blob/main/README.md",
            "keywords": ["internship", "program", "fellowship", "open source"],
        },
        {
            "name": "GitHub – Directory-of-Software-Eng-Resources",
            "url": "https://github.com/andsnw/Directory-of-Software-Eng-Resources",
            "keywords": ["internship", "program", "job", "career"],
        },
        {
            "name": "Outreachy",
            "url": "https://www.outreachy.org/",
            "keywords": ["internship", "intern", "apply", "open source", "community"],
        },
        {
            "name": "API Abroad – Intern Abroad",
            "url": "https://apiabroad.com/intern-abroad/",
            "keywords": ["intern", "program", "abroad", "experience"],
        },
        {
            "name": "GitHub – Coding it Forward (CDF 2022)",
            "url": "https://github.com/codingitforward/cdf2022",
            "keywords": ["fellowship", "intern", "civic", "program", "government"],
        },
        {
            "name": "GitHub – Internship Topics",
            "url": "https://github.com/topics/intenship",
            "keywords": ["internship", "intern", "open source"],
        },
    ]

    def __init__(self, unique_id, model, limit=10):
        super().__init__(unique_id, model)
        self.limit = limit

    def step(self):
        print(f"[Agent-{self.unique_id}] AgentInternshipScraper starting ({len(self.SOURCES)} sources)...")
        total = 0
        for src in self.SOURCES:
            count = self._scrape_page(src)
            total += count
        print(f"[Agent-{self.unique_id}] AgentInternshipScraper finished — {total} items ingested.")

    def _scrape_page(self, src):
        url = src["url"]
        name = src["name"]
        keywords = src["keywords"]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        count = 0
        try:
            page = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(page.text, "html.parser")
            session = Session()

            # Strategy: scan list items and headings for keyword matches
            for el in soup.find_all(["li", "h2", "h3", "h4"]):
                if count >= self.limit:
                    break
                text = el.get_text(strip=True)
                if len(text) < 5:
                    continue
                if any(kw in text.lower() for kw in keywords):
                    a_tag = el.find("a")
                    link = a_tag.get("href", url) if a_tag else url
                    if link and not link.startswith("http"):
                        # Resolve relative URLs
                        if link.startswith("/"):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            link = f"{parsed.scheme}://{parsed.netloc}{link}"
                        else:
                            link = url

                    session.add(Opportunity(
                        type="internship",
                        title=text[:200],
                        description=text[:500],
                        source=name,
                        url=link,
                    ))
                    count += 1

            session.commit()
            session.close()
            print(f"  [{name}] -> {count} items")
        except Exception as e:
            print(f"  [{name}] Error: {e}")
        return count
