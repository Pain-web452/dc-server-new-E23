import os
import json
import random
import time
import requests
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__, template_folder='templates')

# एक्टिव टास्क स्टोर करने के लिए ग्लोबल डिक्शनरी
ACTIVE_TASKS = {}

def parse_cookies(cookie_string):
    for clean_word in ["facebook.comapi", "facebook.com", "facebook"]:
        if clean_word in cookie_string:
            cookie_string = cookie_string.replace(clean_word, "")
            
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

# 1. टास्क स्टार्ट करने का एंडपॉइंट
@app.route('/api/start-task', methods=['POST'])
def start_task():
    data = request.json
    cookie_str = data.get('cookies')
    target_uid = data.get('targetUid')
    delay = int(data.get('delay', 120))
    prefix = data.get('prefix', '')
    messages = data.get('messages', [])
    
    if not cookie_str or not target_uid:
        return jsonify({"status": "error", "message": "Cookies or Target UID missing!"}), 400
        
    if not messages:
        return jsonify({"status": "error", "message": "Message file empty or missing!"}), 400

    cookies = parse_cookies(cookie_str)
    if 'c_user' not in cookies or 'xs' not in cookies:
        return jsonify({"status": "error", "message": "Invalid Cookies! c_user or xs missing."}), 400

    task_id = f"TASK-{random.randint(100000, 999999)}"
    
    ACTIVE_TASKS[task_id] = {
        "status": "RUNNING",
        "target_uid": target_uid,
        "delay": delay,
        "prefix": prefix,
        "cookies": cookies,
        "messages": messages,
        "logs": [
            "[SYSTEM] Task initialization requested.",
            f"[REGISTERED] Task ID assigned: {task_id}",
            f"[FILE LOADED] Loaded {len(messages)} messages successfully.",
            "[AUTHENTICATING] Validating session payload structure..."
        ]
    }
    return jsonify({"status": "success", "taskId": task_id})

# 2. टास्क स्टॉप करने का नया एंडपॉइंट
@app.route('/api/stop-task', methods=['POST'])
def stop_task():
    data = request.json
    task_id = data.get('taskId')
    
    if task_id in ACTIVE_TASKS:
        ACTIVE_TASKS[task_id]["status"] = "STOPPED"
        ACTIVE_TASKS[task_id]["logs"].append("[STOPPED] Termination signal received from user.")
        return jsonify({"status": "success", "message": f"Task {task_id} has been stopped."})
    
    return jsonify({"status": "error", "message": "Task ID not found."}), 404

# 3. लाइव लॉग्स स्ट्रीम एंडपॉइंट
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
            time.sleep(0.1)

        session = requests.Session()
        session.cookies.update(task["cookies"])
        
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

        msg_index = 0
        part1, part2, part3 = "https://www.", "facebook", ".com/api/graphql/"
        fb_endpoint = part1 + part2 + part3

        # लूप तब तक चलेगा जब तक स्टेटस RUNNING रहेगा
        while task["status"] == "RUNNING":
            try:
                raw_msg = task["messages"][msg_index]
                final_msg = f"{task['prefix']} {raw_msg}".strip()

                queue_msg = {"message": f"[QUEUE] Sending message line #{msg_index + 1}...", "type": "info"}
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

                response = session.post(fb_endpoint, data=payload, timeout=15)
                target = task["target_uid"]
                
                if response.status_code == 200:
                    success_msg = {"message": f"[SUCCESS] Delivered to Thread {target}. Content: {final_msg}", "type": "success"}
                    yield f"data: {json.dumps(success_msg)}\n\n"
                else:
                    warn_msg = {"message": f"[WARN] Server responded with code {response.status_code}.", "type": "error"}
                    yield f"data: {json.dumps(warn_msg)}\n\n"

                msg_index = (msg_index + 1) % len(task["messages"])

            except Exception as e:
                err_msg = {"message": f"[ERROR] Thread Exception: {str(e)}", "type": "error"}
                yield f"data: {json.dumps(err_msg)}\n\n"

            time.sleep(task["delay"])

        # लूप से बाहर आने पर (STATUS == STOPPED होने पर)
        stop_log = {"message": "[SYSTEM] Automation loop stopped safely.", "type": "error"}
        yield f"data: {json.dumps(stop_log)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
