import os
import time
import threading
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Real-time task monitoring storage
active_tasks = {}

def messenger_sender_task(cookie, target, prefix, messages, delay):
    task_key = target
    active_tasks[task_key]['total'] = len(messages)
    
    headers = {
        'cookie': cookie,
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://mbasic.facebook.com/'
    }
    
    session = requests.Session()
    
    for idx, msg in enumerate(messages):
        if active_tasks[task_key]['status'] in ['Completed', 'Stopped']:
            break
            
        final_msg = f"{prefix} {msg.strip()}" if prefix else msg.strip()
        
        try:
            # Clean Static Absolute Paths - No replacement logics applied
            url = f"https://facebook.com{target}"
            response = session.get(url, headers=headers)
            
            fb_dtsg = ""
            if 'name="fb_dtsg" value="' in response.text:
                fb_dtsg = response.text.split('name="fb_dtsg" value="')[1].split('"')[0]
                
            send_action_url = "https://facebook.com?"
            payload = {
                'fb_dtsg': fb_dtsg,
                'body': final_msg,
                'send': 'Send'
            }
            
            session.post(send_action_url, headers=headers, data=payload)
            active_tasks[task_key]['sent'] += 1
            active_tasks[task_key]['status'] = 'Running'
            
        except Exception as err:
            active_tasks[task_key]['status'] = f"Failed: {str(err)}"
            break
            
        if idx < len(messages) - 1:
            time.sleep(int(delay))
            
    if active_tasks[task_key]['status'] == 'Running':
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
        
    active_tasks[target] = {
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

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(active_tasks)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
