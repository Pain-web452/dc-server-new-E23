import os
import time
import threading
import re
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# रीयल-टाइम टास्क मॉनिटरिंग स्टोरेज
active_tasks = {}

def extract_thread_id(target_input):
    """
    इनपुट से थ्रेड आईडी (UID) निकालता है।
    चाहे पूरा URL हो, इनबॉक्स पाथ हो या सिर्फ ID, यह मुख्य ID को फ़िल्टर कर लेता है।
    """
    # अगर पूरा URL या क्वेरी स्ट्रिंग है तो tid या id निकालता है
    match = re.search(r'(?:tid=|t_id=|id=)([0-9a-fA-F:\-_]+|[0-9]+)', target_input)
    if match:
        return match.group(1)
    
    # अगर URL में स्लैश के बाद सिर्फ नंबर हैं (जैसे थ्रेड आईडी डायरेक्ट पाथ में हो)
    path_match = re.findall(r'([0-9]+)', target_input)
    if path_match:
        return path_match[-1] # सबसे आखिरी का नंबर आईडी मान लेते हैं
        
    return target_input.strip()

def messenger_sender_task(cookie, raw_target, prefix, messages, delay):
    thread_id = extract_thread_id(raw_target)
    task_key = thread_id
    
    active_tasks[task_key]['total'] = len(messages)
    
    headers = {
        'cookie': cookie,
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://facebook.com'
    }
    
    session = requests.Session()
    
    for idx, msg in enumerate(messages):
        # **Task Stop चेक**
        if active_tasks.get(task_key, {}).get('status') in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        
        try:
            # URL BUG FIX: यहाँ URL को बिल्कुल साफ और सही स्ट्रक्चर में रखा गया है
            url = f"https://facebook.commessages/read/?tid={thread_id}"
            response = session.get(url, headers=headers)
            
            fb_dtsg = ""
            if 'name="fb_dtsg" value="' in response.text:
                fb_dtsg = response.text.split('name="fb_dtsg" value="')[1].split('"')[0]
                
            # mbasic में मैसेज भेजने का एक्शन फॉर्म URL खोजना
            action_match = re.search(r'action="(/messages/send/\?icm=1[^"]*)"', response.text)
            if action_match:
                send_action_url = f"https://facebook.com{action_match.group(1)}"
            else:
                send_action_url = f"https://facebook.commessages/send/?tid={thread_id}"
                
            payload = {
                'fb_dtsg': fb_dtsg,
                'body': final_msg,
                'send': 'Send'
            }
            
            session.post(send_action_url, headers=headers, data=payload)
            
            if active_tasks.get(task_key):
                active_tasks[task_key]['sent'] += 1
                active_tasks[task_key]['status'] = 'Running'
            
        except Exception as err:
            if active_tasks.get(task_key):
                active_tasks[task_key]['status'] = f"Failed: {str(err)}"
            break
            
        if idx < len(messages) - 1:
            time.sleep(int(delay))
            
    if active_tasks.get(task_key) and active_tasks[task_key]['status'] == 'Running':
        active_tasks[task_key]['status'] = 'Completed'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_automation():
    cookie = request.form.get('cookie')
    target = request.form.get('target') 
    prefix = request.form.get('prefix', '')
    delay = request.form.get('delay', 120)
    
    file = request.files.get('message_file')
    if not file or file.filename == '':
        return "Error: Please upload a valid .txt message file first.", 400
        
    content = file.read().decode('utf-8').splitlines()
    cleaned_messages = [m.strip() for m in content if m.strip()]
    
    if not cleaned_messages:
        return "Error: Uploaded file is empty.", 400
        
    thread_id = extract_thread_id(target)
    
    active_tasks[thread_id] = {
        'sent': 0,
        'total': len(cleaned_messages),
        'status': 'Running'
    }
    
    worker = threading.Thread(
        target=messenger_sender_task, 
        args=(cookie, target, prefix, cleaned_messages, delay)
    )
    worker.daemon = True
    worker.start()
    
    return render_template('index.html')

# चलते हुए टास्क को रोकने का रूट (Stop Task)
@app.route('/stop', methods=['POST'])
def stop_automation():
    target = request.form.get('target')
    thread_id = extract_thread_id(target)
    
    if thread_id in active_tasks:
        active_tasks[thread_id]['status'] = 'Stopped'
        return jsonify({"message": f"Task for ID {thread_id} has been stopped successfully.", "status": "Stopped"})
    
    return jsonify({"error": "No active task found for this ID."}), 404

# सभी टास्क का लाइव स्टेटस देखने का रूट (View Tasks)
@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(active_tasks)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
