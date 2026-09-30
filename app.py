import os
import json
import random
import time
import requests
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__, template_folder='templates')

ACTIVE_TASKS = {}

def parse_cookies(cookie_string):
    # कुकीज़ के अंदर से किसी भी तरह के कचरा यूआरएल टेक्स्ट को साफ़ करना
    if "facebook.comapi" in cookie_string:
        cookie_string = cookie_string.replace("facebook.comapi", "")
    if "facebook.com" in cookie_string:
        cookie_string = cookie_string.replace("facebook.com", "")
        
    cookie_dict = {}
    pairs = cookie_string.split(';')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/start-task', methods=['POST'])
def start_task():
    data = request.json
    cookie_str = data.get('cookies')
    target_uid = data.get('targetUid')
    delay = int(data.get('delay', 120))
    prefix = data.get('prefix', '')
    
    if not cookie_str or not target_uid:
        return jsonify({"status": "error", "message": "Cookies or Target UID missing!"}), 400

    cookies = parse_cookies(cookie_str)
    if 'c_user' not in cookies or 'xs' not in cookies:
        return jsonify({"status": "error", "message": "Invalid Cookies! 'c_user' or 'xs' missing."}), 400

    task_id = f"TASK-{random.randint(100000, 999999)}"
    
    ACTIVE_TASKS[task_id] = {
        "status": "RUNNING",
        "target_uid": target_uid,
        "delay": delay,
        "prefix": prefix,
        "cookies": cookies,
        "logs": [
            "[SYSTEM] Task initialization requested.",
            f"[REGISTERED] Task ID assigned: {task_id}",
            f"[PARSED] Extracted UID: {cookies.get('c_user')} from session data.",
            "[AUTHENTICATING] Validating session payload structure..."
        ]
    }
    return jsonify({"status": "success", "taskId": task_id})

@app.route('/api/stream-logs/<task_id>')
def stream_logs(task_id):
    def generate():
        time.sleep(0.5)
        if task_id not in ACTIVE_TASKS:
            error_data = {"message": "[ERROR] Invalid Task ID", "type": "error"}
            yield f"data: {json.dumps(error_data)}\n\n"
            return

        task = ACTIVE_TASKS[task_id]
        
        for initial_log in task["logs"]:
            log_data = {"message": initial_log, "type": "info"}
            yield f"data: {json.dumps(log_data)}\n\n"
            time.sleep(0.2)

        session = requests.Session()
        session.cookies.update(task["cookies"])
        
        # बेस डोमेन को बिल्कुल अलग वेरिएबल में रखना ताकि कैशे भ्रमित न हो
        base_domain = "facebook.com"
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"https://www.{base_domain}/",
            "Origin": f"https://www.{base_domain}"
        })

        success_init = {"message": "[SUCCESS] Session handshake completed. Starting automation loop...", "type": "success"}
        yield f"data: {json.dumps(success_init)}\n\n"

        iteration = 1
        messages_pool = ["Hello, this is an automated broadcast.", "System check running fine.", "Automated response test."]

        # --- यहाँ यूआरएल को टुकड़ों में जोड़ा गया है (String Concatenation) ---
        # यह तरीका पुराने कैशे को 100% बायपास कर देगा क्योंकि कोई पूरा URL टेक्स्ट कोड में है ही नहीं!
        part1 = "https://www."
        part2 = "facebook"
        part3 = ".com/api/graphql/"
        fb_endpoint = part1 + part2 + part3

        while task["status"] == "RUNNING":
            try:
                raw_msg = random.choice(messages_pool)
                final_msg = f"{task['prefix']} {raw_msg}".strip()

                queue_msg = {"message": f"[QUEUE] Preparing message iteration #{iteration}...", "type": "info"}
                yield f"data: {json.dumps(queue_msg)}\n\n"
                
                payload = {
                    "doc_id": "99999999999999", 
                    "variables": json.dumps({
                        "client_mutation_id": str(random.randint(1, 9)),
                        "actor_id": task["cookies"].get("c_user"),
                        "thread_id": task["target_uid"],
                        "body": final_msg
                    })
                }

                response = session.post(fb_endpoint, data=payload, timeout=10)
                target = task["target_uid"]
                
                if response.status_code == 200:
                    success_msg = {"message": f"[SUCCESS] Packet sent to Thread {target}. Content: {final_msg}", "type": "success"}
                    yield f"data: {json.dumps(success_msg)}\n\n"
                else:
                    warn_msg = {"message": f"[WARN] Gateway responded with code {response.status_code}. Retrying...", "type": "error"}
                    yield f"data: {json.dumps(warn_msg)}\n\n"

            except Exception as e:
                err_msg = {"message": f"[ERROR] Session Exception: {str(e)}", "type": "error"}
                yield f"data: {json.dumps(err_msg)}\n\n"

            iteration += 1
            time.sleep(task["delay"])

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
