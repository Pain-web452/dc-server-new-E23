from flask import Flask, render_template, request, jsonify
import requests
import time
import threading

app = Flask(__name__)

# ग्लोबल वैरिएबल्स जो टास्क को मैनेज करेंगे
is_running = False
live_logs = []
loop_thread = None

def add_log(text):
    time_now = time.strftime("%H:%M:%S")
    log_entry = f"[{time_now}] {text}"
    live_logs.append(log_entry)
    if len(live_logs) > 50:
        live_logs.pop(0)
    print(log_entry)

def send_via_cookie_loop(cookies_data, target_id, delay, messages, hater_name):
    global is_running
    
    cookie_list = [c.strip() for c in cookies_data.split('\n') if c.strip()]
    message_list = [m.strip() for m in messages.split('\n') if m.strip()]
    
    cookie_index = 0
    message_index = 0
    
    add_log("🚀 Cookie-based Automation Loop Started on Render!")

    while is_running:
        current_cookie = cookie_list[cookie_index]
        base_message = message_list[message_index]
        final_message = f"{hater_name} {base_message}" if hater_name else base_message
        
        try:
            fb_ib_url = "https://facebook.com"
            
            # इनबॉक्स थ्रेड में भेजने के लिए फॉर्म डेटा
            payload = {
                't_id': target_id,
                'body': final_message,
                'send': 'Send'
            }
            
            headers = {
                'Cookie': current_cookie,
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mi A3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f'https://facebook.com{target_id}'
            }
            
            response = requests.post(fb_ib_url, data=payload, headers=headers)
            
            if "checkpoint" in response.text or "login_form" in response.text:
                add_log("❌ FAILED: कुकी एक्सपायर हो चुकी है या अकाउंट चेकपॉइंट पर है।")
            else:
                add_log(f"✓ IB SENT SUCCESS: \"{final_message}\"")
                
        except Exception as e:
            add_log(f"❌ CONNECTION ERROR: ({str(e)})")
            
        # इंडेक्स अपडेट करना
        cookie_index = (cookie_index + 1) % len(cookie_list)
        message_index = (message_index + 1) % len(message_list)
        
        # तय समय (Delay) तक रुकना
        time.sleep(int(delay))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_task():
    global is_running, loop_thread, live_logs
    if is_running:
        return jsonify({"status": "Loop already running!"})
        
    data = request.json
    cookies = data.get('cookies')
    target_id = data.get('target_id')
    delay = data.get('delay', 10)
    messages = data.get('messages')
    hater_name = data.get('hater_name', '')
    
    if not cookies or not target_id or not messages:
        return jsonify({"status": "Missing required fields"}), 400
        
    is_running = True
    live_logs = []
    
    # लूप को बैकग्राउंड थ्रेड में चलाना ताकि Render टाइमआउट न दे
    loop_thread = threading.Thread(target=send_via_cookie_loop, args=(cookies, target_id, delay, messages, hater_name))
    loop_thread.daemon = True
    loop_thread.start()
    
    return jsonify({"status": "Loop Initialized"})

@app.route('/api/logs')
def get_logs():
    return jsonify(live_logs)

@app.route('/api/stop', methods=['POST'])
def stop_task():
    global is_running
    is_running = False
    add_log("⛔ Task stopped by user.")
    return jsonify({"status": "Task stopped"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
  
