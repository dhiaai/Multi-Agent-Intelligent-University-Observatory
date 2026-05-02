import os
from sqlalchemy import func
from db_setup import Session, Opportunity, Recommendation, Notification, OpportunityCluster
import json

def deduplicate_opportunities():
    """Removes duplicate opportunities based on URL and Title."""
    session = Session()
    print("Starting deduplication process...")
    
    # Get total count before
    total_before = session.query(Opportunity).count()
    print(f"Total opportunities before: {total_before}")
    
    # We will identify duplicates by grouping by URL and keeping the one with the lowest ID.
    # Alternatively, group by title if URLs are somehow varying. Let's use URL as it's the most robust for scrapers.
    # Wait, some scrapers might not have unique URLs. Let's group by (type, title).
    
    duplicates = session.query(
        Opportunity.type,
        Opportunity.title,
        func.min(Opportunity.id).label('keep_id'),
        func.array_agg(Opportunity.id) if str(session.bind.url).startswith("postgresql") else func.group_concat(Opportunity.id)
    ).group_by(Opportunity.type, Opportunity.title).having(func.count(Opportunity.id) > 1).all()
    
    if not duplicates:
        print("No duplicates found.")
        session.close()
        return
        
    ids_to_delete = []
    
    for row in duplicates:
        # SQLite group_concat returns string "id1,id2", PostgreSQL array_agg returns list
        if isinstance(row[3], str):
            all_ids = [int(x) for x in row[3].split(',')]
        else:
            all_ids = row[3]
            
        keep_id = row[2]
        for opp_id in all_ids:
            if opp_id != keep_id:
                ids_to_delete.append(opp_id)
                
    print(f"Found {len(ids_to_delete)} duplicate records. Deleting...")
    
    if not ids_to_delete:
        session.close()
        return
        
    # Before deleting opportunities, we must clean up foreign keys in Recommendations and Notifications
    session.query(Recommendation).filter(Recommendation.opportunity_id.in_(ids_to_delete)).delete(synchronize_session=False)
    session.query(Notification).filter(Notification.opportunity_id.in_(ids_to_delete)).delete(synchronize_session=False)
    
    # We should also rebuild clusters because member IDs are stored as JSON strings.
    # The easiest way is to just clear clusters and let the user re-run the pipeline.
    session.query(OpportunityCluster).delete()
    
    # Now delete the duplicates
    session.query(Opportunity).filter(Opportunity.id.in_(ids_to_delete)).delete(synchronize_session=False)
    
    session.commit()
    
    total_after = session.query(Opportunity).count()
    print(f"Deduplication complete. Total opportunities after: {total_after}")
    session.close()

if __name__ == "__main__":
    deduplicate_opportunities()
