import os
from flask import Flask, render_template, request, jsonify
from bot_engine import start_bot, stop_bot, get_logs, clear_logs, bot_state

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './'

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": bot_state.get("status", "Stopped"),
        "logs": get_logs()
    })

@app.route("/api/upload_cookies", methods=["POST"])
def api_upload_cookies():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'cookies.json'))
    return jsonify({"status": "cookies_uploaded", "message": "Cookies uploaded successfully"})

@app.route("/api/upload_message", methods=["POST"])
def api_upload_message():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'message.txt'))
    return jsonify({"status": "message_uploaded", "message": "Message file uploaded"})

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
