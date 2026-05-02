import mesa
import requests
from bs4 import BeautifulSoup
from db_setup import Opportunity, Session


class AgentCertificationScraper(mesa.Agent):
    """Collects courses, webinars, certifications from Coursera, GitHub CS courses, MOOC pages."""

    SOURCES = [
        {
            "name": "Coursera – AI/Data Science Courses",
            "url": "https://www.coursera.org/courses?query=artificial+intelligence",
            "keywords": ["course", "certificate", "specialization", "professional", "learn", "ai", "data"],
        },
        {
            "name": "Coursera – MOOC Courses",
            "url": "https://www.coursera.org/courses?query=mooc",
            "keywords": ["course", "certificate", "specialization", "professional", "mooc"],
        },
        {
            "name": "GitHub – CS Video Courses",
            "url": "https://github.com/Developer-Y/cs-video-courses",
            "keywords": ["course", "lecture", "video", "mooc", "tutorial", "university"],
        },
        {
            "name": "ScholarshipsAndGrants.us – MOOC Scholarships",
            "url": "https://scholarshipsandgrants.us/other/scholarships-for-students-pursuing-moocs/",
            "keywords": ["mooc", "course", "certification", "online", "learning"],
        },
    ]

    def __init__(self, unique_id, model, limit=10):
        super().__init__(unique_id, model)
        self.limit = limit

    def step(self):
        print(f"[Agent-{self.unique_id}] AgentCertificationScraper starting ({len(self.SOURCES)} sources)...")
        total = 0
        for src in self.SOURCES:
            count = self._scrape_page(src)
            total += count
        print(f"[Agent-{self.unique_id}] AgentCertificationScraper finished — {total} items ingested.")

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

            for el in soup.find_all(["li", "h2", "h3", "h4", "a"]):
                if count >= self.limit:
                    break
                text = el.get_text(strip=True)
                if len(text) < 5:
                    continue
                if any(kw in text.lower() for kw in keywords):
                    link = el.get("href") if el.name == "a" else None
                    if not link:
                        a_tag = el.find("a")
                        link = a_tag.get("href", url) if a_tag else url
                    if link and not link.startswith("http"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        link = f"{parsed.scheme}://{parsed.netloc}{link}" if link.startswith("/") else url

                    session.add(Opportunity(
                        type="certification_webinar",
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
