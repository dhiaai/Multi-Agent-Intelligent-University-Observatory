from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from sqlalchemy import func
import json
import subprocess

from db_setup import Session, Opportunity, User, OpportunityCluster, Recommendation, Notification, Swipe
from analyze import main as run_analysis
from pipeline import main as run_pipeline
from agents.gemini_agents import generate_cv, generate_cover_letter, generate_interview_prep

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    session = Session()
    try:
        total_opportunities = session.query(Opportunity).count()
        total_users = session.query(User).count()
        total_clusters = session.query(OpportunityCluster).count()
        
        types_dist = session.query(Opportunity.type, func.count(Opportunity.id)).group_by(Opportunity.type).all()
        types_dict = {t[0]: t[1] for t in types_dist}
        
        return jsonify({
            'totalOpportunities': total_opportunities,
            'totalUsers': total_users,
            'totalClusters': total_clusters,
            'opportunitiesByType': types_dict
        })
    finally:
        session.close()

@app.route('/api/clusters', methods=['GET'])
def get_clusters():
    session = Session()
    try:
        clusters = session.query(OpportunityCluster).all()
        result = []
        for c in clusters:
            members = json.loads(c.members)
            result.append({
                'id': c.cluster_id,
                'name': c.cluster_name,
                'size': len(members)
            })
        result.sort(key=lambda x: x['size'], reverse=True)
        return jsonify(result)
    finally:
        session.close()

@app.route('/api/clusters/graph', methods=['GET'])
def get_clusters_graph():
    session = Session()
    try:
        clusters = session.query(OpportunityCluster).all()
        opportunities_query = session.query(Opportunity).all()
        opp_dict = {opp.id: opp for opp in opportunities_query}
        
        nodes = []
        links = []
        
        for c in clusters:
            members = json.loads(c.members)
            if not members:
                continue
                
            cluster_node_id = f"cluster_{c.cluster_id}"
            nodes.append({
                'id': cluster_node_id,
                'name': c.cluster_name,
                'group': c.cluster_id,
                'type': 'cluster',
                'size': 20
            })
            
            for m_id in members:
                opp = opp_dict.get(m_id)
                if opp:
                    opp_node_id = f"opp_{opp.id}"
                    nodes.append({
                        'id': opp_node_id,
                        'name': opp.title,
                        'url': opp.url,
                        'group': c.cluster_id,
                        'type': 'opportunity',
                        'size': 10
                    })
                    links.append({
                        'source': opp_node_id,
                        'target': cluster_node_id
                    })
        return jsonify({'nodes': nodes, 'links': links})
    finally:
        session.close()

# --- User Management CRUD ---

@app.route('/api/users', methods=['GET'])
def get_users():
    session = Session()
    try:
        users = session.query(User).all()
        result = [{'id': u.user_id, 'name': u.name, 'profile': u.profile, 'skills': u.skills, 'interests': u.interests} for u in users]
        return jsonify(result)
    finally:
        session.close()

@app.route('/api/users', methods=['POST'])
def add_user():
    session = Session()
    try:
        data = request.json
        user = User(
            name=data['name'],
            profile=data.get('profile', ''),
            interests=data.get('interests', ''),
            skills=data.get('skills', '')
        )
        session.add(user)
        session.commit()
        return jsonify({'id': user.user_id, 'name': user.name})
    finally:
        session.close()

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    session = Session()
    try:
        data = request.json
        user = session.query(User).get(user_id)
        if user:
            user.name = data.get('name', user.name)
            user.profile = data.get('profile', user.profile)
            user.interests = data.get('interests', user.interests)
            user.skills = data.get('skills', user.skills)
            session.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'User not found'}), 404
    finally:
        session.close()

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    session = Session()
    try:
        user = session.query(User).get(user_id)
        if user:
            session.query(Recommendation).filter_by(user_id=user_id).delete()
            session.query(Notification).filter_by(user_id=user_id).delete()
            session.query(Swipe).filter_by(user_id=user_id).delete()
            session.delete(user)
            session.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'User not found'}), 404
    finally:
        session.close()

# --- Feed ---

@app.route('/api/users/<int:user_id>/recommendations', methods=['GET'])
def get_recommendations(user_id):
    session = Session()
    try:
        recs = session.query(Recommendation, Opportunity)\
                      .join(Opportunity, Recommendation.opportunity_id == Opportunity.id)\
                      .filter(Recommendation.user_id == user_id)\
                      .order_by(Recommendation.score.desc())\
                      .limit(10).all()
        
        result = []
        for rec, opp in recs:
            result.append({
                'id': opp.id,
                'title': opp.title,
                'type': opp.type,
                'source': opp.source,
                'tags': opp.tags,
                'score': round(rec.score, 3)
            })
        return jsonify(result)
    finally:
        session.close()

@app.route('/api/users/<int:user_id>/notifications', methods=['GET'])
def get_notifications(user_id):
    session = Session()
    try:
        notifs = session.query(Notification, Opportunity)\
                        .join(Opportunity, Notification.opportunity_id == Opportunity.id)\
                        .filter(Notification.user_id == user_id, Notification.status == 'unread')\
                        .order_by(Notification.timestamp.desc()).all()
        
        result = []
        for n, opp in notifs:
            result.append({
                'id': n.notification_id,
                'title': opp.title,
                'type': opp.type,
                'timestamp': n.timestamp.isoformat() if n.timestamp else None
            })
        return jsonify(result)
    finally:
        session.close()

# --- Swipe Deck ---

@app.route('/api/users/<int:user_id>/swipe-deck', methods=['GET'])
def get_swipe_deck(user_id):
    """Get unswiped opportunities for a user, ordered by recommendation score."""
    session = Session()
    try:
        swiped_ids = [s.opportunity_id for s in session.query(Swipe).filter_by(user_id=user_id).all()]
        
        query = session.query(Opportunity)
        if swiped_ids:
            query = query.filter(~Opportunity.id.in_(swiped_ids))
        
        # Try to order by recommendation score
        recs = session.query(Recommendation).filter_by(user_id=user_id).all()
        rec_scores = {r.opportunity_id: r.score for r in recs}
        
        opps = query.all()
        result = []
        for opp in opps:
            result.append({
                'id': opp.id,
                'title': opp.title,
                'type': opp.type,
                'description': (opp.description or '')[:300],
                'source': opp.source,
                'location': opp.location,
                'tags': opp.tags,
                'url': opp.url,
                'score': round(rec_scores.get(opp.id, 0), 3)
            })
        result.sort(key=lambda x: x['score'], reverse=True)
        return jsonify(result[:50])  # max 50 cards
    finally:
        session.close()

@app.route('/api/users/<int:user_id>/swipe', methods=['POST'])
def record_swipe(user_id):
    """Record a swipe action (liked/rejected)."""
    session = Session()
    try:
        data = request.json
        from datetime import datetime, timezone
        swipe = Swipe(
            user_id=user_id,
            opportunity_id=data['opportunity_id'],
            action=data['action'],
            timestamp=datetime.now(timezone.utc)
        )
        session.add(swipe)
        session.commit()
        return jsonify({'success': True})
    finally:
        session.close()

@app.route('/api/users/<int:user_id>/liked', methods=['GET'])
def get_liked(user_id):
    """Get all liked opportunities for a user."""
    session = Session()
    try:
        liked = session.query(Swipe, Opportunity)\
                       .join(Opportunity, Swipe.opportunity_id == Opportunity.id)\
                       .filter(Swipe.user_id == user_id, Swipe.action == 'liked').all()
        result = []
        for s, opp in liked:
            result.append({
                'id': opp.id,
                'title': opp.title,
                'type': opp.type,
                'description': (opp.description or '')[:200],
                'tags': opp.tags,
                'url': opp.url
            })
        return jsonify(result)
    finally:
        session.close()

# --- AI Career Agents ---

@app.route('/api/generate/cv', methods=['POST'])
def api_generate_cv():
    session = Session()
    try:
        data = request.json
        user = session.query(User).get(data['user_id'])
        opp = session.query(Opportunity).get(data['opportunity_id'])
        if not user or not opp:
            return jsonify({'error': 'User or opportunity not found'}), 404
        html = generate_cv(user.name, user.skills, user.interests, user.profile, opp.title, opp.description or '', opp.type)
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/generate/cover-letter', methods=['POST'])
def api_generate_cover_letter():
    session = Session()
    try:
        data = request.json
        user = session.query(User).get(data['user_id'])
        opp = session.query(Opportunity).get(data['opportunity_id'])
        if not user or not opp:
            return jsonify({'error': 'User or opportunity not found'}), 404
        html = generate_cover_letter(user.name, user.skills, user.interests, user.profile, opp.title, opp.description or '', opp.type)
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/generate/interview-prep', methods=['POST'])
def api_generate_interview_prep():
    session = Session()
    try:
        data = request.json
        user = session.query(User).get(data['user_id'])
        opp = session.query(Opportunity).get(data['opportunity_id'])
        if not user or not opp:
            return jsonify({'error': 'User or opportunity not found'}), 404
        html = generate_interview_prep(user.name, user.skills, user.interests, user.profile, opp.title, opp.description or '', opp.type)
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

# --- SSE Pipeline Stream ---

@app.route('/api/stream-pipeline', methods=['GET'])
def stream_pipeline():
    targets_str = request.args.get('targets', '')
    targets = targets_str.split(',') if targets_str else []
    
    def generate():
        yield f"data: {json.dumps({'status': 'info', 'message': 'Initializing Observer Agents...'})}\n\n"
        
        cmd = ["venv\\Scripts\\python", "pipeline.py"]
        if targets:
            cmd.extend(["--targets"] + targets)
            
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                yield f"data: {json.dumps({'status': 'progress', 'message': line.strip()})}\n\n"
        process.stdout.close()
        process.wait()
        
        yield f"data: {json.dumps({'status': 'info', 'message': 'Initializing Analysis Agents...'})}\n\n"
        
        process2 = subprocess.Popen(["venv\\Scripts\\python", "analyze.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in iter(process2.stdout.readline, ''):
            if line.strip():
                yield f"data: {json.dumps({'status': 'progress', 'message': line.strip()})}\n\n"
        process2.stdout.close()
        process2.wait()
        
        yield f"data: {json.dumps({'status': 'success', 'message': 'Pipeline Complete!'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
