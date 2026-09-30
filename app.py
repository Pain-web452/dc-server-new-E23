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
    चाहे पूरा URL हो या सिर्फ ID, यह मुख्य ID को फ़िल्टर कर लेता है।
    """
    # अगर पूरा URL दिया गया हो तो tid या t_id या ID निकालता है
    match = re.search(r'(?:tid=設cid\.|tid=|t_id=|messages\/read\/?\?id=)([0-9a-fA-F:\-_]+|[0-9]+)', target_input)
    if match:
        return match.group(1)
    # अगर केवल नंबर या ID दी गई हो
    clean_id = target_input.strip().replace('/', '')
    return clean_id

def messenger_sender_task(cookie, raw_target, prefix, messages, delay):
    # इनबॉक्स URL या इनपुट से मुख्य UID/Thread ID निकालना
    thread_id = extract_thread_id(raw_target)
    task_key = thread_id
    
    # टास्क को इनिशियलाइज करना
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
        # **Task Stop चेक**: यदि यूजर ने टास्क रोक दिया है तो लूप से बाहर निकलें
        if active_tasks.get(task_key, {}).get('status') in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        
        try:
            # mbasic फेसबुक इनबॉक्स का सही सेंडिंग URL स्ट्रक्चर
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
            
            # टास्क प्रोग्रेस अपडेट करना
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
    target = request.form.get('target') # यहाँ पूरा इनबॉक्स लिंक या UID डाल सकते हैं
    prefix = request.form.get('prefix', '')
    delay = request.form.get('delay', 120)
    
    file = request.files.get('message_file')
    if not file or file.filename == '':
        return "Error: Please upload a valid .txt message file first.", 400
        
    content = file.read().decode('utf-8').splitlines()
    cleaned_messages = [m.strip() for m in content if m.strip()]
    
    if not cleaned_messages:
        return "Error: Uploaded file is empty.", 400
        
    # टारगेट से UID निकालकर उसे टास्क की की (Key) बनाना
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

# **नया रूट**: चल रहे टास्क को रोकने के लिए (Stop Task)
@app.route('/stop', methods=['POST'])
def stop_automation():
    target = request.form.get('target')
    thread_id = extract_thread_id(target)
    
    if thread_id in active_tasks:
        active_tasks[thread_id]['status'] = 'Stopped'
        return jsonify({"message": f"Task for ID {thread_id} has been stopped successfully.", "status": "Stopped"})
    
    return jsonify({"error": "No active task found for this ID."}), 404

# **नया रूट**: सभी टास्क को देखने या कोड स्टेटस चेक करने के लिए (View Tasks)
@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(active_tasks)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
