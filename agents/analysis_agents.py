import mesa
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime, timezone

from db_setup import Session, Opportunity, User, OpportunityCluster, Recommendation, Notification

class AgentClassifier(mesa.Agent):
    """
    Reads opportunities, extracts keywords via TF-IDF, and updates the tags column.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
    def classify(self):
        print(f"[{self.__class__.__name__}] Starting classification...")
        session = Session()
        opportunities = session.query(Opportunity).all()
        
        if not opportunities:
            print("No opportunities to classify.")
            session.close()
            return

        # Prepare corpus
        corpus = []
        opp_ids = []
        for opp in opportunities:
            text = f"{opp.title} {opp.description or ''}"
            corpus.append(text)
            opp_ids.append(opp.id)
            
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = np.array(vectorizer.get_feature_names_out())
        
        # Extract top keywords for each opportunity
        for i, opp_id in enumerate(opp_ids):
            row = tfidf_matrix[i].toarray().flatten()
            top_indices = row.argsort()[-5:][::-1] # top 5
            top_keywords = feature_names[top_indices]
            
            # Simple domain classification based on keywords
            domain = "General STEM"
            keywords_joined = " ".join(top_keywords).lower()
            if any(k in keywords_joined for k in ['ai', 'machine learning', 'neural', 'nlp']):
                domain = "AI / Machine Learning"
            elif any(k in keywords_joined for k in ['data', 'analytics', 'statistics']):
                domain = "Data Science"
            elif any(k in keywords_joined for k in ['web', 'react', 'frontend', 'backend']):
                domain = "Web Development"
                
            tags = list(top_keywords) + [domain]
            
            # Update DB
            opp = session.query(Opportunity).get(opp_id)
            opp.tags = ", ".join(tags)
            
        session.commit()
        print(f"[{self.__class__.__name__}] Extracted tags for {len(opportunities)} opportunities.")
        session.close()
        
    def cluster(self): pass
    def match(self): pass
    def advise(self): pass
    def notify(self): pass


class AgentCluster(mesa.Agent):
    """
    Groups opportunities into clusters using KMeans.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
    def cluster(self):
        print(f"[{self.__class__.__name__}] Starting clustering...")
        session = Session()
        
        # Clear old clusters
        session.query(OpportunityCluster).delete()
        
        opportunities = session.query(Opportunity).all()
        if len(opportunities) < 8:
            print("Not enough data to cluster.")
            session.close()
            return
            
        corpus = [f"{opp.title} {opp.tags}" for opp in opportunities]
        vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        X = vectorizer.fit_transform(corpus)
        
        k = min(10, len(opportunities))
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        kmeans.fit(X)
        
        feature_names = vectorizer.get_feature_names_out()
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        
        for i in range(k):
            # Extract top 3 words for cluster name
            top_words = [feature_names[ind] for ind in order_centroids[i, :3]]
            cluster_name = " ".join(top_words).title()
            
            # Find members
            members = [opp.id for j, opp in enumerate(opportunities) if kmeans.labels_[j] == i]
            
            cluster = OpportunityCluster(
                cluster_name=cluster_name,
                members=json.dumps(members)
            )
            session.add(cluster)
            
        session.commit()
        print(f"[{self.__class__.__name__}] Created {k} clusters.")
        session.close()

    def classify(self): pass
    def match(self): pass
    def advise(self): pass
    def notify(self): pass


class AgentRelevanceMatcher(mesa.Agent):
    """
    Computes user-opportunity relevance scores.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
    def match(self):
        print(f"[{self.__class__.__name__}] Computing relevance scores...")
        session = Session()
        
        # Clear old recommendations to recompute
        session.query(Recommendation).delete()
        
        users = session.query(User).all()
        opportunities = session.query(Opportunity).all()
        
        if not users or not opportunities:
            print("Missing users or opportunities.")
            session.close()
            return
            
        opp_corpus = [f"{opp.title} {opp.description or ''} {opp.tags or ''}" for opp in opportunities]
        user_corpus = [f"{u.interests or ''} {u.skills or ''} {u.profile or ''}" for u in users]
        
        vectorizer = TfidfVectorizer(stop_words='english')
        # Fit on everything to get a common vocabulary
        vectorizer.fit(opp_corpus + user_corpus)
        
        opp_vectors = vectorizer.transform(opp_corpus)
        user_vectors = vectorizer.transform(user_corpus)
        
        # Cosine similarity matrix: shape (num_users, num_opportunities)
        sim_matrix = cosine_similarity(user_vectors, opp_vectors)
        
        recs_added = 0
        for i, user in enumerate(users):
            for j, opp in enumerate(opportunities):
                score = float(sim_matrix[i, j])
                if score > 0.05: # Slight threshold to save space
                    rec = Recommendation(
                        user_id=user.user_id,
                        opportunity_id=opp.id,
                        score=score
                    )
                    session.add(rec)
                    recs_added += 1
                    
        session.commit()
        print(f"[{self.__class__.__name__}] Generated {recs_added} recommendations.")
        session.close()

    def classify(self): pass
    def cluster(self): pass
    def advise(self): pass
    def notify(self): pass


class AgentAdvisor(mesa.Agent):
    """
    Outputs ranked recommendations for users.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
    def advise(self):
        print(f"[{self.__class__.__name__}] Generating advice reports...")
        session = Session()
        users = session.query(User).all()
        
        print("\n" + "="*60)
        print("  ADVISOR RECOMMENDATIONS")
        print("="*60)
        
        # Let's just do it for 2 sample users to avoid spamming console
        for user in users[:2]:
            print(f"\nUser: {user.name} | Skills: {user.skills}")
            recs = session.query(Recommendation, Opportunity)\
                          .join(Opportunity, Recommendation.opportunity_id == Opportunity.id)\
                          .filter(Recommendation.user_id == user.user_id)\
                          .order_by(Recommendation.score.desc())\
                          .limit(5).all()
            
            for i, (rec, opp) in enumerate(recs, 1):
                print(f"  {i}. [Score: {rec.score:.2f}] {opp.title} ({opp.type})")
                print(f"     Tags: {opp.tags}")
        print("="*60 + "\n")
        session.close()

    def classify(self): pass
    def cluster(self): pass
    def match(self): pass
    def notify(self): pass


class AgentNotification(mesa.Agent):
    """
    Detects new relevant opportunities and creates notifications.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
    def notify(self):
        print(f"[{self.__class__.__name__}] Checking for notifications...")
        session = Session()
        
        # In a real app, we'd only look at opportunities fetched since the last run.
        # For simulation, we'll notify users for their top matches (score > 0.3)
        # if they don't already have a notification.
        
        # Find matches with score > 0.3
        strong_matches = session.query(Recommendation).filter(Recommendation.score > 0.3).all()
        
        notifs_created = 0
        for match in strong_matches:
            # Check if notification exists
            existing = session.query(Notification).filter_by(
                user_id=match.user_id,
                opportunity_id=match.opportunity_id
            ).first()
            
            if not existing:
                notif = Notification(
                    user_id=match.user_id,
                    opportunity_id=match.opportunity_id,
                    status="unread",
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(notif)
                notifs_created += 1
                
        session.commit()
        print(f"[{self.__class__.__name__}] Created {notifs_created} new notifications.")
        session.close()

    def classify(self): pass
    def cluster(self): pass
    def match(self): pass
    def advise(self): pass
