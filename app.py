import os
import json
from flask import Flask, render_template, request, jsonify
from bot_engine import start_bot, stop_bot, get_logs, clear_logs, bot_state

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": bot_state.get("status", "Stopped"),
        "logs": get_logs()
    })

@app.route("/api/save_cookies", methods=["POST"])
def api_save_cookies():
    """Cookies ko text box se lekar cookies.json mein save karta hai."""
    data = request.json
    cookies_text = data.get("cookies", "").strip()
    
    if not cookies_text:
        return jsonify({"error": "Cookies khali hai"}), 400
    
    try:
        # JSON validate karein
        parsed = json.loads(cookies_text)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format. Sahi JSON daalein"}), 400
    
    # File mein save karein
    with open("cookies.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    
    return jsonify({"status": "saved", "message": "✅ Cookies save ho gayi"})

@app.route("/api/save_message", methods=["POST"])
def api_save_message():
    """Message ko text box se lekar message.txt mein save karta hai."""
    data = request.json
    message_text = data.get("message", "").strip()
    
    if not message_text:
        return jsonify({"error": "Message khali hai"}), 400
    
    with open("message.txt", "w", encoding="utf-8") as f:
        f.write(message_text)
    
    return jsonify({"status": "saved", "message": "✅ Message save ho gaya"})

@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.json
    group_id = str(data.get("group_id", "")).strip()
    interval = int(data.get("interval", 3600))
    
    if not group_id:
        return jsonify({"error": "Group ID required"}), 400
    
    result = start_bot(group_id, interval)
    return jsonify(result)

@app.route("/api/stop", methods=["POST"])
def api_stop():
    return jsonify(stop_bot())

@app.route("/api/clear_logs", methods=["POST"])
def api_clear_logs():
    clear_logs()
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
