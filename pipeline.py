"""
pipeline.py — Data Ingestion Pipeline
Orchestrates 5 Mesa scraper agents, each targeting different opportunity types.
Usage:  python pipeline.py
"""
import mesa
from agents.internship_scraper import AgentInternshipScraper
from agents.project_scraper import AgentProjectScraper
from agents.scholarship_scraper import AgentScholarshipScraper
from agents.certification_scraper import AgentCertificationScraper
from agents.postdoc_scraper import AgentPostdocScraper
from db_setup import init_db, Session, Opportunity


import argparse

class DataIngestionModel(mesa.Model):
    """A Mesa model hosting specialized scraper agents."""

    def __init__(self, limit_per_agent=10, targets=None):
        super().__init__()
        self.schedule = mesa.time.RandomActivation(self)
        
        agent_map = {
            'internship': AgentInternshipScraper,
            'project': AgentProjectScraper,
            'scholarship': AgentScholarshipScraper,
            'certification': AgentCertificationScraper,
            'postdoc': AgentPostdocScraper
        }
        
        targets = targets or list(agent_map.keys())
        
        for i, target in enumerate(targets):
            if target in agent_map:
                self.schedule.add(agent_map[target](i+1, self, limit=limit_per_agent))

    def step(self):
        """Advance the model by one step — every agent scrapes once."""
        self.schedule.step()

def main():
    parser = argparse.ArgumentParser(description="Run the data ingestion pipeline.")
    parser.add_argument('--targets', nargs='+', help="List of scraper types to run (e.g. internship project)")
    args = parser.parse_args()
    
    # 1. Ensure tables exist
    print("=" * 60)
    print("  Intelligent University Observatory — Data Ingestion")
    print("=" * 60)
    init_db()

    # 2. Run the scraper agents
    targets = args.targets if args.targets else None
    print(f"\n--- Running scraper agents. Targets: {targets or 'ALL'} ---\n")
    model = DataIngestionModel(limit_per_agent=10, targets=targets)
    model.step()

    # 3. Report
    session = Session()
    total = session.query(Opportunity).count()
    print("\n" + "=" * 60)
    print(f"  Pipeline complete. Total opportunities in DB: {total}")
    print("=" * 60)
    session.close()

if __name__ == "__main__":
    main()
