import os
import time
import threading
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

SERVER_START_TIME = time.time()
active_tasks = {}

def extract_thread_id(target_input):
    if not target_input:
        return "UNKNOWN_TASK"
    match_slash = re.search(r'([0-9]{10,})', target_input)
    if match_slash:
        return f"TASK-{match_slash.group(1)[:5]}"
    return "TASK-1"

def messenger_sender_task(cookie, raw_target, prefix, messages, delay, pin, task_id):
    active_tasks[task_id]['total'] = len(messages)
    thread_id = raw_target.strip()
    
    headers = {
        'cookie': cookie,
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
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
            # URL सही किया गया (/ लगाया गया)
            url = f"https://facebook.com/messages/read/?tid={thread_id}"
            response = session.get(url, headers=headers)
            
            fb_dtsg = ""
            if 'name="fb_dtsg" value="' in response.text:
                fb_dtsg = response.text.split('name="fb_dtsg" value="')[1].split('"')[0]
                
            action_match = re.search(r'action="(/messages/send/\?icm=1[^"]*)"', response.text)
            if action_match:
                send_action_url = f"https://facebook.com{action_match.group(1)}"
            else:
                send_action_url = f"https://facebook.com/messages/send/?tid={thread_id}"
                
            payload = {'fb_dtsg': fb_dtsg, 'body': final_msg, 'send': 'Send'}
            if pin: 
                payload['pin'] = pin
                
            session.post(send_action_url, headers=headers, data=payload)
            
            if active_tasks.get(task_id):
                active_tasks[task_id]['sent'] += 1
                active_tasks[task_id]['status'] = 'Running'
                log_entry = f"[{current_time}] ✅ Sent:\n\"{final_msg}\""
                active_tasks[task_id]['logs'].append(log_entry)
            
        except Exception as err:
            if active_tasks.get(task_id):
                active_tasks[task_id]['status'] = 'Stopped'
                active_tasks[task_id]['logs'].append(f"[{current_time}] ❌ Error: {str(err)}")
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
    
    # टास्क इनिशियलाइज़ेशन और थ्रेड स्टार्ट
    active_tasks[task_id] = {
        'status': 'Pending',
        'total': len(cleaned_messages),
        'sent': 0,
        'logs': []
    }
    
    thread = threading.Thread(
        target=messenger_sender_task, 
        args=(cookie, target, prefix, cleaned_messages, delay, pin, task_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "task_id": task_id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
