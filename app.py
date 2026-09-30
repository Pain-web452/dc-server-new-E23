import os
import json
import random
import time
from flask import Flask, render_template, request, jsonify, Response
from playwright.sync_api import sync_playwright

app = Flask(__name__, template_folder='templates')

ACTIVE_TASKS = {}

def parse_cookies(cookie_string):
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
        "cookie_str": cookie_str,
        "logs": [
            f"[SYSTEM] Task initialization requested.",
            f"[REGISTERED] Task ID assigned: {task_id}",
            f"[PREPARING] Initializing headless browser core for safety..."
        ]
    }
    return jsonify({"status": "success", "taskId": task_id})

@app.route('/api/stream-logs/<task_id>')
def stream_logs(task_id):
    def generate():
        if task_id not in ACTIVE_TASKS:
            yield f"data: {json.dumps({'message': '[ERROR] Invalid Task ID', 'type': 'error'})}\n\n"
            return

        task = ACTIVE_TASKS[task_id]
        
        for initial_log in task["logs"]:
            yield f"data: {json.dumps({'message': initial_log, 'type': 'info'})}\n\n"
            time.sleep(0.4)

        yield f"data: {json.dumps({'message': '[BROWSER] Launching isolated environment...', 'type': 'info'})}\n\n"

        # Playwright ब्राउज़र इंजन शुरू करना
        with sync_playwright() as p:
            # बिना स्क्रीन दिखे बैकग्राउंड में ब्राउज़र चलाना
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            
            # फेसबुक के लिए कुकीज़ फॉर्मेट तैयार करना
            cookies_list = []
            parsed_cookies = parse_cookies(task["cookie_str"])
            for name, value in parsed_cookies.items():
                cookies_list.append({
                    "name": name,
                    "value": value,
                    "domain": ".facebook.com",
                    "path": "/"
                })

            # ब्राउज़र कॉन्टेक्स्ट बनाना और कुकीज़ डालना
            context = browser.new_context()
            context.add_cookies(cookies_list)
            page = context.new_page()

            yield f"data: {json.dumps({'message': '[SUCCESS] Cookies injected into browser session.', 'type': 'success'})}\n\n"

            iteration = 1
            messages_pool = ["Hello! This is an automated secure broadcast.", "Automated inbox delivery active.", "System check running fine."]

            while task["status"] == "RUNNING":
                try:
                    raw_msg = random.choice(messages_pool)
                    final_msg = f"{task['prefix']} {raw_msg}".strip()

                    yield f"data: {json.dumps({'message': f'[QUEUE] Navigating to target inbox stream...', 'type': 'info'})}\n\n"
                    
                    # सीधे मैसेंजर चैट लिंक पर जाना (m.me या messenger.com)
                    page.goto(f"https://messenger.com{task['target_uid']}", wait_until="networkidle")
                    time.sleep(3)

                    # चेक करना कि क्या हम सच में चैट पेज पर हैं
                    if "login" in page.url:
                        yield f"data: {json.dumps({'message': '[ERROR] Facebook rejected cookies! Session Expired. Please extract new cookies.', 'type': 'error'})}\n\n"
                        break

                    # चैट बॉक्स ढूंढना और मैसेज टाइप करके सेंड बटन दबाना (फेसबुक के इनपुट सिलेक्टर्स के अनुसार)
                    # नोट: ये सिलेक्टर्स फेसबुक के वेब लेआउट के अनुसार बदलते रहते हैं
                    chat_box = page.locator('div[role="textbox"]')
                    if chat_box.is_visible():
                        chat_box.fill(final_msg)
                        page.keyboard.press("Enter")
                        yield f"data: {json.dumps({'message': f'[SUCCESS] Message delivered to IB thread {task[\'target_uid\']}: {final_msg}', 'type': 'success'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'message': '[WARN] Chat input box not found or hidden. Retrying...', 'type': 'error'})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'message': f'[EXCEPTION] Flow error: {str(e)}', 'type': 'error'})}\n\n"

                iteration += 1
                time.sleep(task["delay"])

            browser.close()

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
                        
