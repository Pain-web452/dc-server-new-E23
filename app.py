import os
import time
import threading
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

SERVER_START_TIME = time.time()
active_tasks = {}

def extract_thread_id(target_input):
    if not target_input:
        return "UNKNOWN_TASK"
    match_slash = re.search(r'([0-9]{10,})', target_input)
    if match_slash:
        return match_slash.group(1)
    return target_input.strip()

def messenger_sender_task(cookies_list, raw_target, prefix, messages, delay, pin, task_id):
    active_tasks[task_id]['total'] = len(messages)
    thread_id = extract_thread_id(raw_target)
    
    current_cookie_idx = 0
    total_cookies = len(cookies_list)
    
    session = requests.Session()
    
    for idx, msg in enumerate(messages):
        if active_tasks.get(task_id, {}).get('status') in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        
        message_sent = False
        while not message_sent and current_cookie_idx < total_cookies:
            current_time = datetime.now().strftime("%I:%M:%S %p")
            cookie = cookies_list[current_cookie_idx].strip()
            
            headers = {
                'cookie': cookie,
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'referer': 'https://facebook.com'
            }
            
            try:
                # 🛑 URL BUG FIX: यहाँ डोमेन को बिल्कुल सही (://facebook.com) फिक्स कर दिया गया है
                url = f"https://facebook.commessages/read/?tid={thread_id}"
                response = session.get(url, headers=headers)
                
                if "login_form" in response.text or "checkpoint" in response.text or not response.text:
                    raise Exception(f"Cookie-{current_cookie_idx + 1} Deactivated/Expired")
                
                if "enter_pin" in response.text or "pin" in response.text or "secure" in response.text:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    pin_form = soup.find('form')
                    if pin_form:
                        pin_action = "https://://facebook.com" + pin_form['action']
                        pin_payload = {}
                        for input_tag in pin_form.find_all('input'):
                            if input_tag.get('name'):
                                pin_payload[input_tag['name']] = input_tag.get('value', '')
                        if pin:
                            pin_payload['pin'] = pin
                            response = session.post(pin_action, headers=headers, data=pin_payload)

                soup = BeautifulSoup(response.text, 'html.parser')
                form = soup.find('form', action=re.compile(r'/messages/send/'))
                
                if not form:
                    raise Exception(f"Cookie-{current_cookie_idx + 1} Blocked from Inbox Form")
                    
                action_url = "https://://facebook.com" + form['action']
                payload = {}
                for input_tag in form.find_all('input'):
                    if input_tag.get('name'):
                        payload[input_tag['name']] = input_tag.get('value', '')
                        
                payload['body'] = final_msg
                payload['send'] = 'Send'
                
                send_response = session.post(action_url, headers=headers, data=payload)
                
                if "error" in send_response.url or "checkpoint" in send_response.url:
                    raise Exception("Facebook blocked the message post request")
                
                if active_tasks.get(task_id):
                    active_tasks[task_id]['sent'] += 1
                    active_tasks[task_id]['status'] = 'Running'
                    log_entry = f"[{current_time}] ✅ Sent via ID-{current_cookie_idx + 1}:\n\"{final_msg}\""
                    active_tasks[task_id]['logs'].append(log_entry)
                
                message_sent = True
                
            except Exception as err:
                fail_time = datetime.now().strftime("%I:%M:%S %p")
                active_tasks[task_id]['logs'].append(f"[{fail_time}] ⚠️ {str(err)}. Switching Cookie...")
                current_cookie_idx += 1
                
        if not message_sent:
            if active_tasks.get(task_id):
                active_tasks[task_id]['status'] = 'Stopped'
                active_tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%I:%M:%S %p')}] ❌ All Cookies Deactivated/Expired. Process Stopped.")
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
    cookie_data = request.form.get('cookie')
    target = request.form.get('target') 
    prefix = request.form.get('prefix', '')
    delay = request.form.get('delay', 120)
    pin = request.form.get('pin', '')
    
    cookies_list = [c.strip() for c in cookie_data.splitlines() if c.strip()]
    if not cookies_list:
        return "Error: Please provide at least one valid cookie string.", 400
        
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
        args=(cookies_list, target, prefix, cleaned_messages, delay, pin, task_id)
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
    return jsonify({"tasks": active_tasks, "uptime": uptime_string})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
