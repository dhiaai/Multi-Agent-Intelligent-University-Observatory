import mesa
import requests
from bs4 import BeautifulSoup
from db_setup import Opportunity, Session


class AgentScholarshipScraper(mesa.Agent):
    """Collects scholarships from all URLs in the markdown: API Abroad (4 pages), GitHub (2 repos), MOOC scholarships."""

    SOURCES = [
        {
            "name": "API Abroad – Scholarships",
            "url": "https://apiabroad.com/scholarships/",
            "keywords": ["scholarship", "fund", "award", "grant", "apply"],
        },
        {
            "name": "API Abroad – Learning Experience Scholarship",
            "url": "https://apiabroad.com/learning-experience-scholarship/",
            "keywords": ["scholarship", "learning", "experience", "award", "apply"],
        },
        {
            "name": "API Abroad – Early Bird Scholarship",
            "url": "https://apiabroad.com/api-early-bird-scholarship-terms/",
            "keywords": ["scholarship", "early", "bird", "term", "eligible", "award"],
        },
        {
            "name": "API Abroad – Academic Excellence Scholarship",
            "url": "https://apiabroad.com/academic-excellence-scholarship-terms/",
            "keywords": ["scholarship", "academic", "excellence", "term", "eligible"],
        },
        {
            "name": "GitHub – Resources-for-Students",
            "url": "https://github.com/navyaarora01/Resources-for-Students",
            "keywords": ["scholarship", "fellowship", "grant", "fund", "award"],
        },
        {
            "name": "GitHub – Directory-of-Software-Eng-Resources",
            "url": "https://github.com/andsnw/Directory-of-Software-Eng-Resources",
            "keywords": ["scholarship", "fellowship", "grant", "fund"],
        },
        {
            "name": "ScholarshipsAndGrants.us – MOOC Scholarships",
            "url": "https://scholarshipsandgrants.us/other/scholarships-for-students-pursuing-moocs/",
            "keywords": ["scholarship", "mooc", "fund", "grant", "online"],
        },
    ]

    def __init__(self, unique_id, model, limit=10):
        super().__init__(unique_id, model)
        self.limit = limit

    def step(self):
        print(f"[Agent-{self.unique_id}] AgentScholarshipScraper starting ({len(self.SOURCES)} sources)...")
        total = 0
        for src in self.SOURCES:
            count = self._scrape_page(src)
            total += count
        print(f"[Agent-{self.unique_id}] AgentScholarshipScraper finished — {total} items ingested.")

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

            for el in soup.find_all(["li", "h2", "h3", "h4", "p"]):
                if count >= self.limit:
                    break
                text = el.get_text(strip=True)
                if len(text) < 5:
                    continue
                if any(kw in text.lower() for kw in keywords):
                    a_tag = el.find("a")
                    link = a_tag.get("href", url) if a_tag else url
                    if link and not link.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        link = f"{parsed.scheme}://{parsed.netloc}{link}" if link.startswith("/") else url

                    session.add(Opportunity(
                        type="scholarship",
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
