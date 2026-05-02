import os
from sqlalchemy import func
from db_setup import Session, Opportunity, Recommendation, Notification, OpportunityCluster
import json

def deduplicate_opportunities():
    """Removes duplicate opportunities based on URL and Title."""
    session = Session()
    print("Starting deduplication process...")
    
    total_before = session.query(Opportunity).count()
    print(f"Total opportunities before: {total_before}")
    
    # We will use window functions or subqueries if needed, but for simplicity:
    opportunities = session.query(Opportunity).all()
    
    seen = set()
    ids_to_delete = []
    
    for opp in opportunities:
        # Create a unique key for deduplication
        key = (opp.type, opp.title.strip().lower())
        if key in seen:
            ids_to_delete.append(opp.id)
        else:
            seen.add(key)
            
    print(f"Found {len(ids_to_delete)} duplicate records. Deleting...")
    
    if not ids_to_delete:
        session.close()
        return
        
    # Before deleting opportunities, clean up foreign keys
    session.query(Recommendation).filter(Recommendation.opportunity_id.in_(ids_to_delete)).delete(synchronize_session=False)
    session.query(Notification).filter(Notification.opportunity_id.in_(ids_to_delete)).delete(synchronize_session=False)
    
    # Rebuild clusters is recommended after deleting members, so we just delete clusters
    session.query(OpportunityCluster).delete()
    
    # Now delete the duplicates
    session.query(Opportunity).filter(Opportunity.id.in_(ids_to_delete)).delete(synchronize_session=False)
    
    session.commit()
    
    total_after = session.query(Opportunity).count()
    print(f"Deduplication complete. Total opportunities after: {total_after}")
    session.close()

if __name__ == "__main__":
    deduplicate_opportunities()
