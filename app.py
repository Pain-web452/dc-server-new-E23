import os
import time
import threading
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# सर्वर शुरू होने का समय (Uptime के लिए)
SERVER_START_TIME = time.time()

# रीयल-टाइम टास्क मॉनिटरिंग स्टोरेज
active_tasks = {}

def extract_thread_id(target_input):
    if not target_input:
        return "UNKNOWN_TASK"
    # अगर पूरा URL या पाथ दिया गया हो तो उसमें से नंबर निकालता है
    match_slash = re.search(r'([0-9]{10,})', target_input)
    if match_slash:
        return match_slash.group(1)
    return target_input.strip()

def messenger_sender_task(cookie, raw_target, prefix, messages, delay, pin, task_id):
    active_tasks[task_id]['total'] = len(messages)
    thread_id = extract_thread_id(raw_target)
    
    headers = {
        'cookie': cookie,
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://facebook.com'
    }
    
    session = requests.Session()
    
    for idx, msg in enumerate(messages):
        if active_tasks.get(task_id, {}).get('status') in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        current_time = datetime.now().strftime("%I:%M:%S %p")
        
        try:
            # 1. इनबॉक्स पेज को लोड करना ताकि फॉर्म टोकन्स मिल सकें
            url = f"https://facebook.commessages/read/?tid={thread_id}"
            response = session.get(url, headers=headers)
            
            # BeautifulSoup से पूरे पेज का फॉर्म पार्स करना
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form', action=re.compile(r'/messages/send/'))
            
            if not form:
                # यदि इनबॉक्स फॉर्म नहीं मिला, तो हो सकता है कुकी एक्सपायर हो गई हो
                raise Exception("Cookie Expired or Invalid Thread ID (Form not found)")
            
            # फॉर्म का सही एक्शन URL निकालना
            action_url = "https://facebook.com" + form['action']
            
            # फॉर्म के सभी हिडन इनपुट्स (fb_dtsg, jazoest, tids आदि) को ऑटो-कैप्चर करना
            payload = {}
            for input_tag in form.find_all('input'):
                if input_tag.get('name'):
                    payload[input_tag['name']] = input_tag.get('value', '')
            
            # टेक्स्ट एरिया/मैसेज बॉडी और सेंड बटन सेट करना
            payload['body'] = final_msg
            payload['send'] = 'Send'
            
            # यदि एंड-टू-एंड पिन की फ़ील्ड मौजूद हो
            if pin:
                payload['pin'] = pin
            
            # 2. सही टोकन्स के साथ मैसेज पोस्ट करना
            send_response = session.post(action_url, headers=headers, data=payload)
            
            # वेरिफिकेशन: चेक करना कि क्या मैसेज सच में डिलीवर हुआ या फेसबुक ने ब्लॉक किया
            if "error" in send_response.url or "checkpoint" in send_response.url:
                raise Exception("Facebook blocked the request or security checkpoint triggered")
            
            # टास्क प्रोग्रेस और टर्मिनल लॉग अपडेट करना
            if active_tasks.get(task_id):
                active_tasks[task_id]['sent'] += 1
                active_tasks[task_id]['status'] = 'Running'
                log_entry = f"[{current_time}] ✅ Sent:\n\"{final_msg}\""
                active_tasks[task_id]['logs'].append(log_entry)
            
        except Exception as err:
            if active_tasks.get(task_id):
                active_tasks[task_id]['status'] = 'Stopped'
                active_tasks[task_id]['logs'].append(f"[{current_time}] ❌ Failed: {str(err)}")
            break
            
        if idx < len(messages) - 1:
            time.sleep(int(delay))
            
    if active_tasks.get(task_id) and active_tasks[task_id]['status'] == 'Running':
        active_tasks[task_id]['status'] = 'Completed'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_automation():
    cookie = request.form.get('cookie')
    target = request.form.get('target') 
    prefix = request.form.get('prefix', '')
    delay = request.form.get('delay', 120)
    pin = request.form.get('pin', '')
    
    file = request.files.get('message_file')
    if not file or file.filename == '':
        return "Error: Please upload a file.", 400
        
    content = file.read().decode('utf-8').splitlines()
    cleaned_messages = [m.strip() for m in content if m.strip()]
    
    task_idx = len(active_tasks) + 1
    task_id = f"TASK-{task_idx}"
    
    active_tasks[task_id] = {
        'sent': 0,
        'total': len(cleaned_messages),
        'status': 'Running',
        'logs': []
    }
    
    worker = threading.Thread(
        target=messenger_sender_task, 
        args=(cookie, target, prefix, cleaned_messages, delay, pin, task_id)
    )
    worker.daemon = True
    worker.start()
    
    return render_template('index.html')

@app.route('/stop', methods=['POST'])
def stop_automation():
    task_id = request.form.get('task_id')
    if task_id in active_tasks:
        active_tasks[task_id]['status'] = 'Stopped'
        active_tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%I:%M:%S %p')}] 🛑 Task Stopped by User.")
        return jsonify({"message": "Stopped", "status": "Stopped"})
    return jsonify({"error": "Not found"}), 404

@app.route('/status', methods=['GET'])
def get_status():
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    uptime_string = f"{days}d {hours}h {minutes}m {seconds}s"
    
    return jsonify({
        "tasks": active_tasks,
        "uptime": uptime_string
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
