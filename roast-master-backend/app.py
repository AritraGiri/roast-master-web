"""
app.py — Roast Master AI: Flask Backend
========================================
Handles user sessions, Heat Level logic, and routing to the Orchestrator.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from asgiref.sync import async_to_sync
import uuid

# Import the logic from your second file
from orchestrator import run_multi_agent_pipeline

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://aritragiri.github.io"]}})  # Critical for frontend communication

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

@app.route("/profile", methods=["POST"])
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
        # expect these four keys. Passing the full `user` dict would leak `heat`
        # and `message_count` into the f-strings inside orchestrator.py.
        user_profile = {
            "name"   : user["name"],
            "major"  : user["major"],
            "tech"   : user["tech"],
            "hotTake": user["hotTake"],
        }

        # Call the Async Orchestrator from the Sync Flask route
        result = async_to_sync(run_multi_agent_pipeline)(
            message,
            user_profile,   # ← clean slice, not the raw `user` dict
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

@app.route("/")
def home():
    return "Roast Master AI backend is running 🔥"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
