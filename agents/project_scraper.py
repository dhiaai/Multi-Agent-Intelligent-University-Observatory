import mesa
import requests
from bs4 import BeautifulSoup
from db_setup import Opportunity, Session


class AgentProjectScraper(mesa.Agent):
    """Collects research projects / funders via OpenAlex API, Crossref API, and GitHub API lists."""

    def __init__(self, unique_id, model, limit=10):
        super().__init__(unique_id, model)
        self.limit = limit

    def step(self):
        print(f"[Agent-{self.unique_id}] AgentProjectScraper starting (3 sources)...")
        total = 0
        total += self._scrape_openalex_funders()
        total += self._scrape_crossref_works()
        total += self._scrape_github_api_list()
        print(f"[Agent-{self.unique_id}] AgentProjectScraper finished — {total} items ingested.")

    # ------------------------------------------------------------------
    def _scrape_openalex_funders(self):
        """Query OpenAlex /funders endpoint for research funding bodies."""
        url = f"https://api.openalex.org/funders?per_page={self.limit}"
        count = 0
        try:
            res = requests.get(url, timeout=15)
            data = res.json()
            session = Session()
            for item in data.get("results", []):
                title = item.get("display_name", "Unknown Funder")
                desc = item.get("description", "") or ""
                country = item.get("country_code", "Unknown")
                oa_id = item.get("id", "")
                session.add(Opportunity(
                    type="research_project",
                    title=f"Funding: {title}",
                    description=desc[:500],
                    source="OpenAlex API – Funders",
                    location=country,
                    url=oa_id,
                ))
                count += 1
            session.commit()
            session.close()
            print(f"  [OpenAlex API – Funders] -> {count} items")
        except Exception as e:
            print(f"  [OpenAlex API – Funders] Error: {e}")
        return count

    # ------------------------------------------------------------------
    def _scrape_crossref_works(self):
        """Query Crossref for recent AI/Data-Science research works."""
        url = (
            "https://api.crossref.org/works"
            "?query=artificial+intelligence+data+science"
            f"&rows={self.limit}"
            "&sort=published&order=desc"
        )
        count = 0
        try:
            res = requests.get(url, timeout=15)
            data = res.json()
            items = data.get("message", {}).get("items", [])
            session = Session()
            for item in items:
                title_parts = item.get("title", ["Untitled"])
                title = title_parts[0] if title_parts else "Untitled"
                desc = ", ".join(item.get("subject", []))
                link = item.get("URL", "")
                session.add(Opportunity(
                    type="research_project",
                    title=title[:200],
                    description=desc[:500] if desc else "Crossref scholarly work",
                    source="Crossref API",
                    url=link,
                ))
                count += 1
            session.commit()
            session.close()
            print(f"  [Crossref API] -> {count} items")
        except Exception as e:
            print(f"  [Crossref API] Error: {e}")
        return count

    # ------------------------------------------------------------------
    def _scrape_github_api_list(self):
        """Scrape the curated API-mega-list repo for research/data APIs."""
        url = "https://github.com/cporter202/API-mega-list"
        headers = {"User-Agent": "Mozilla/5.0"}
        count = 0
        try:
            page = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(page.text, "html.parser")
            session = Session()
            for li in soup.find_all("li"):
                if count >= self.limit:
                    break
                text = li.get_text(strip=True)
                a_tag = li.find("a")
                if a_tag and any(kw in text.lower() for kw in ("research", "data", "science", "api", "academic")):
                    link = a_tag.get("href", url)
                    if not link.startswith("http"):
                        link = "https://github.com" + link if link.startswith("/") else url
                    session.add(Opportunity(
                        type="research_project",
                        title=text[:200],
                        description=text[:500],
                        source="GitHub – API-mega-list",
                        url=link,
                    ))
                    count += 1
            session.commit()
            session.close()
            print(f"  [GitHub – API-mega-list] -> {count} items")
        except Exception as e:
            print(f"  [GitHub – API-mega-list] Error: {e}")
        return count
