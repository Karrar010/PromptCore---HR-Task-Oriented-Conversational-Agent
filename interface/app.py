"""
Web interface for HR Conversational Agent.
Flask-based web application for interacting with the HR agent.
"""

from flask import Flask, render_template, request, jsonify, session
import uuid
import os
import sys

# Add parent directory to path to import app module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import HRConversationalAgent

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hr-agent-secret-key-change-in-production")

# Store active agents per session
active_agents = {}


def get_or_create_agent(session_id: str, user_id: str = None, channel: str = None):
    """Get or create an HR agent for the session."""
    if session_id not in active_agents:
        active_agents[session_id] = HRConversationalAgent(
            conversation_id=str(uuid.uuid4()),
            user_id=user_id or f"user_{session_id}",
            channel=channel or "web",
            platform="web"
        )
    return active_agents[session_id]


@app.route('/')
def index():
    """Render the main chat interface."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages from the user."""
    try:
        # Get session ID
        session_id = session.get('session_id', str(uuid.uuid4()))
        if 'session_id' not in session:
            session['session_id'] = session_id
        
        # Get user message
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Get or create agent
        agent = get_or_create_agent(session_id)
        
        # Process message
        response = agent.process_message(user_message)
        
        # Get conversation state
        conversation_state = agent.get_conversation_state()
        
        return jsonify({
            'success': True,
            'response': response['response_text'],
            'action': response.get('action', ''),
            'conversation_state': conversation_state,
            'conversation_id': response.get('conversation_id')
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current conversation state."""
    try:
        session_id = session.get('session_id')
        if not session_id or session_id not in active_agents:
            return jsonify({
                'success': True,
                'state': None,
                'message': 'No active conversation'
            })
        
        agent = active_agents[session_id]
        conversation_state = agent.get_conversation_state()
        
        return jsonify({
            'success': True,
            'state': conversation_state
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the conversation."""
    try:
        session_id = session.get('session_id')
        if session_id and session_id in active_agents:
            del active_agents[session_id]
        
        # Create new session ID
        session['session_id'] = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'message': 'Conversation reset'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("HR Conversational Agent Web Interface")
    print("=" * 60)
    
    # Pre-load all models before starting server
    try:
        from utils.model_loader import preload_models
        print("\nPre-loading models for faster responses...")
        preload_models()
    except Exception as e:
        print(f"Warning: Could not pre-load models: {e}")
        print("Models will be loaded on first use (may be slower)")
    
    print("\n" + "=" * 60)
    print("Starting server on http://localhost:5000")
    print("Open your browser and navigate to http://localhost:5000")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

