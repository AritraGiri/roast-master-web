"""
app.py — Roast Master AI: Flask Backend
========================================
Handles user sessions, Heat Level logic, and routing to the Orchestrator.
Includes Flask-Limiter to prevent API spamming and credit drain.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from asgiref.sync import async_to_sync
import uuid

# Import the logic from your second file
from orchestrator import run_multi_agent_pipeline

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CORS CONFIGURATION (Restricted to your deployment domains)
# ══════════════════════════════════════════════════════════════════════════════
CORS(app, resources={r"/*": {"origins": [
    "https://roast-master-frontend-gqv9.onrender.com",
    "https://aritragiri.github.io"
]}})  # Critical for frontend communication

# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER CONFIGURATION (Anti-Spam Shield)
# ══════════════════════════════════════════════════════════════════════════════
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["60 per minute", "200 per day"],  # Global safety net
    storage_uri="memory://"
)

# In-memory storage for the hackathon session
users = {}

def get_user_or_create(session_id):
    if session_id not in users:
        users[session_id] = {
            "name": "Unknown",
            "major": "Unknown",
            "tech": "Unknown",
            "hotTake": "Unknown",
            "heat": 10,
            "message_count": 0
        }
    return users[session_id]

# ══════════════════════════════════════════════════════════════════════════════
# ROUTING & ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
@limiter.exempt  # Allow anyone to ping the homepage root without counting against limits
def home():
    return "Roast Master AI backend is running 🔥"

@app.route("/profile", methods=["POST"])
@limiter.limit("5 per minute")  # Prevents bot accounts from creating endless profile sessions
def profile():
    data = request.json
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    # Initialize user profile with the 'ammunition' for the roast
    users[session_id] = {
        "name": data.get("name", "Unknown"),
        "major": data.get("major", "Unknown"),
        "tech": data.get("tech", "Unknown"),
        "hotTake": data.get("hotTake", "Unknown"),
        "heat": 10,
        "message_count": 0
    }
    return jsonify({"success": True, "message": "Victim profile registered."})

@app.route("/chat", methods=["POST"])
@limiter.limit("5 per minute")  # Protects your heavy, concurrent multi-agent AI engine from spam
def chat():
    data = request.json
    session_id = data.get("session_id")
    message = data.get("message", "")

    user = get_user_or_create(session_id)
    user["message_count"] += 1

    # Logic: Heat increases faster as the conversation continues
    increase = 12 + (user["message_count"] // 2) * 4
    user["heat"] = min(100, user["heat"] + increase)

    try:
        # Build a clean profile slice — the orchestrator's prompt builders only
        # expect these four keys.
        user_profile = {
            "name"   : user["name"],
            "major"  : user["major"],
            "tech"   : user["tech"],
            "hotTake": user["hotTake"],
        }

        # Call the Async Orchestrator from the Sync Flask route
        result = async_to_sync(run_multi_agent_pipeline)(
            message,
            user_profile,
            user["heat"]
        )
        
        return jsonify({
            "reply": result["roast"],
            "heat": user["heat"],
            "agent_updates": result["agent_previews"]
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "reply": "The AI is currently laughing too hard at your profile to respond. Try again.",
            "heat": user["heat"],
            "agent_updates": ["Error", "Error", "Error"]
        }), 500

@app.route("/giveup", methods=["POST"])
def giveup():
    session_id = request.json.get("session_id")
    if session_id in users:
        user = users[session_id]
        user["heat"] = 10
        user["message_count"] = 0
        return jsonify({
            "reply": f"Mercy granted, {user['name']}. Pathetic.",
            "heat": 10
        })
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    # Never leave debug=True in production!
    app.run(host="0.0.0.0", port=10000, debug=False)
