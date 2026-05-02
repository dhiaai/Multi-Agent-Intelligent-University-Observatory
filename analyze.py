import mesa
import nltk
from agents.analysis_agents import AgentClassifier, AgentCluster, AgentRelevanceMatcher, AgentAdvisor, AgentNotification

def download_nltk_data():
    """Ensure required NLTK data is downloaded."""
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("[analyze] Downloading NLTK stopwords...")
        nltk.download('stopwords', quiet=True)

class AnalysisModel(mesa.Model):
    """
    Orchestrates the analysis pipeline using StagedActivation.
    """
    def __init__(self):
        super().__init__()
        # Define the exact stages in order
        stages = ["classify", "cluster", "match", "advise", "notify"]
        self.schedule = mesa.time.StagedActivation(self, stage_list=stages)
        
        # Instantiate and add agents
        classifier = AgentClassifier(1, self)
        clusterer = AgentCluster(2, self)
        matcher = AgentRelevanceMatcher(3, self)
        advisor = AgentAdvisor(4, self)
        notifier = AgentNotification(5, self)
        
        self.schedule.add(classifier)
        self.schedule.add(clusterer)
        self.schedule.add(matcher)
        self.schedule.add(advisor)
        self.schedule.add(notifier)
        
    def step(self):
        """Advance the model by one step (runs all stages in sequence)."""
        self.schedule.step()

def main():
    print("=" * 60)
    print("  Intelligent University Observatory — Analysis Pipeline")
    print("=" * 60)
    
    download_nltk_data()
    
    print("\n--- Running Analysis Agents ---\n")
    model = AnalysisModel()
    model.step()
    
    print("\n" + "=" * 60)
    print("  Analysis Pipeline Complete.")
    print("=" * 60)

if __name__ == "__main__":
    main()
