import os
import time
import threading
import re
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

SERVER_START_TIME = time.time()
active_tasks = {}

# एंटी-बैन प्रोटेक्शन के लिए अलग-अलग मोबाइल ब्राउज़र्स के हेडर
USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 Chrome/92.0.4515.166 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1'
]

def extract_target_id(target_input):
    if not target_input:
        return "UNKNOWN_TARGET"
    # अगर यूजर ग्रुप या इनबॉक्स का पूरा URL डालता है, तो आईडी फ़िल्टर कर लेता है
    match = re.search(r'(?:groups/|id=|tid=)([0-9]{10,})', target_input)
    if match:
        return match.group(1)
    return target_input.strip()

def messenger_group_sender_task(all_cookies, target_id, prefix, messages, delay, task_id):
    active_tasks[task_id]['total'] = len(messages)
    current_cookie_idx = 0
    total_cookies = len(all_cookies)
    session = requests.Session()
    
    for idx, msg in enumerate(messages):
        if active_tasks.get(task_id, {}).get('status') in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        message_sent = False
        
        while not message_sent and current_cookie_idx < total_cookies:
            current_time = datetime.now().strftime("%I:%M:%S %p")
            cookie = all_cookies[current_cookie_idx].strip()
            
            headers = {
                'cookie': cookie,
                'user-agent': random.choice(USER_AGENTS),
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'referer': 'https://facebook.com'
            }
            
            try:
                # mbasic पर ग्रुप और इनबॉक्स दोनों को ऑटो-डिटेक्ट करने का लॉजिक
                # यदि आईडी बहुत बड़ी है या टारगेट ग्रुप जैसा लग रहा है
                if len(target_id) > 12: 
                    url = f"https://facebook.comgroups/{target_id}"
                    response = session.get(url, headers=headers)
                    form_action_keyword = r'/a/group/add/'
                    message_field_name = 'xc_message'
                    submit_button_name = 'view_post'
                    submit_button_value = 'Post'
                else:
                    url = f"https://facebook.commessages/read/?tid={target_id}"
                    response = session.get(url, headers=headers)
                    form_action_keyword = r'/messages/send/'
                    message_field_name = 'body'
                    submit_button_name = 'send'
                    submit_button_value = 'Send'

                # क्या आईडी डीएक्टिवेट या लॉगआउट हो चुकी है
                if "login_form" in response.text or "checkpoint" in response.text or not response.text:
                    raise Exception("Cookie Session Expired/Deactivated")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                form = soup.find('form', action=re.compile(form_action_keyword))
                
                if not form:
                    raise Exception("Dynamic form token blocked or Restricted target ID")
                    
                action_url = "https://facebook.com" + form['action']
                payload = {}
                for input_tag in form.find_all('input'):
                    if input_tag.get('name'):
                        payload[input_tag['name']] = input_tag.get('value', '')
                
                payload[message_field_name] = final_msg
                payload[submit_button_name] = submit_button_value
                
                send_response = session.post(action_url, headers=headers, data=payload)
                
                if "error" in send_response.url or "checkpoint" in send_response.url:
                    raise Exception("Facebook Spam checkpoint triggered")
                
                if active_tasks.get(task_id):
                    active_tasks[task_id]['sent'] += 1
                    active_tasks[task_id]['status'] = 'Running'
                    cookie_label = f"Primary ID ({target_id[:5]})" if current_cookie_idx == 0 else f"Backup ID-{current_cookie_idx}"
                    log_entry = f"[{current_time}] ✅ Sent via {cookie_label}:\n\"{final_msg}\""
                    active_tasks[task_id]['logs'].append(log_entry)
                
                message_sent = True
                
            except Exception as err:
                fail_time = datetime.now().strftime("%I:%M:%S %p")
                label = "Primary ID" if current_cookie_idx == 0 else f"Backup ID-{current_cookie_idx}"
                active_tasks[task_id]['logs'].append(f"[{fail_time}] ⚠️ {label} Failed ({str(err)}). Auto Switching...")
                current_cookie_idx += 1
                
        if not message_sent:
            if active_tasks.get(task_id):
                active_tasks[task_id]['status'] = 'Stopped'
                active_tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%I:%M:%S %p')}] ❌ All provided cookies died. Task terminated.")
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
    primary_cookie = request.form.get('cookie', '')
    backup_cookies = request.form.get('backup_cookies', '')
    target = request.form.get('target') 
    prefix = request.form.get('prefix', '')
    delay = request.form.get('delay', 10)
    
    all_cookies = []
    if primary_cookie.strip():
        all_cookies.append(primary_cookie.strip())
    
    for c in backup_cookies.splitlines():
        if c.strip():
            all_cookies.append(c.strip())
            
    if not all_cookies:
        return "Error: Please paste a valid cookie string.", 400

    cleaned_messages = []
    direct_messages = request.form.get('direct_messages', '')
    if direct_messages.strip():
        cleaned_messages = [m.strip() for m in direct_messages.splitlines() if m.strip()]
    else:
        file = request.files.get('message_file')
        if file and file.filename != '':
            content = file.read().decode('utf-8').splitlines()
            cleaned_messages = [m.strip() for m in content if m.strip()]
            
    if not cleaned_messages:
        return "Error: Messages or txt file not found.", 400
        
    target_id = extract_target_id(target)
    task_id = f"TASK-{len(active_tasks) + 1}"
    
    active_tasks[task_id] = {
        'sent': 0,
        'total': len(cleaned_messages),
        'status': 'Running',
        'logs': []
    }
    
    worker = threading.Thread(
        target=messenger_group_sender_task, 
        args=(all_cookies, target_id, prefix, cleaned_messages, delay, task_id)
    )
    worker.daemon = True
    worker.start()
    
    return render_template('index.html')

@app.route('/stop', methods=['POST'])
def stop_automation():
    task_id = request.form.get('task_id')
    if task_id in active_tasks:
        active_tasks[task_id]['status'] = 'Stopped'
        active_tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%I:%M:%S %p')}] 🛑 Task Stopped.")
        return jsonify({"message": "Stopped"})
    return jsonify({"error": "Not found"}), 404

@app.route('/status', methods=['GET'])
def get_status():
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    return jsonify({
        "tasks": active_tasks, 
        "uptime": f"{days}d {hours}h {minutes}m {seconds}s"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
