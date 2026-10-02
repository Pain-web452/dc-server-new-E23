from flask import Flask, render_template, request, jsonify
import requests
import time
import threading

app = Flask(__name__)

is_running = False
live_logs = []
loop_thread = None

def add_log(prefix_tag, text):
    time_now = time.strftime("%H:%M:%S")
    # पहली इमेज के अनुसार लॉग फॉर्मेट तैयार करना
    log_entry = f"<span style='color:#ff007f;'>{prefix_tag}</span><br>[{time_now} AM] ✅ Sent:<br>\"{text}\"<br>-----------------------"
    live_logs.append(log_entry)
    if len(live_logs) > 50:
        live_logs.pop(0)

def send_e2ee_loop(cookies, target_id, delay, messages, prefix, e2ee_pin):
    global is_running
    
    cookie_list = [c.strip() for c in cookies.split('\n') if c.strip()]
    message_list = [m.strip() for m in messages.split('\n') if m.strip()]
    
    cookie_index = 0
    message_index = 0
    
    while is_running:
        current_cookie = cookie_list[cookie_index]
        base_message = message_list[message_index]
        
        # मैसेज प्रीफिक्स जोड़ना (जैसे [RAJ] TESTING E2EE)
        final_message = f"{prefix} {base_message}" if prefix else base_message
        
        try:
            # E2EE मैसेंजर थ्रेड्स के लिए mbasic या graphql के थ्रू फॉर्म सबमिशन हैंडल करना
            fb_url = "https://facebook.com"
            
            payload = {
                't_id': target_id,
                'body': final_message,
                'send': 'Send'
            }
            
            # अगर E2EE पिन मौजूद है, तो पेलोड में पिन की क्रेडेंशियल्स सिंक की जाती हैं
            if e2ee_pin:
                payload['e2ee_pin'] = e2ee_pin

            headers = {
                'Cookie': current_cookie,
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f'https://facebook.com{target_id}'
            }
            
            response = requests.post(fb_url, data=payload, headers=headers)
            
            if "checkpoint" in response.text or "login_form" in response.text:
                add_log("SYSTEM ERROR", "कुकी एक्सपायर हो चुकी है या फेसबुक ने ब्लॉक किया है।")
            else:
                # स्क्रीनशॉट में दिखने वाला लॉग प्रीफिक्स "R3TIR3D FYT3R"
                log_prefix = prefix if prefix else "MESSENGER BOT"
                add_log(log_prefix, final_message)
                
        except Exception as e:
            add_log("ERROR", f"सेंड फेल हुआ: {str(e)}")
            
        cookie_index = (cookie_index + 1) % len(cookie_list)
        message_index = (message_index + 1) % len(message_list)
        
        time.sleep(int(delay))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_task():
    global is_running, loop_thread, live_logs
    if is_running:
        return jsonify({"status": "Already running"})
        
    data = request.json
    cookies = data.get('cookies')
    target_id = data.get('target_id')
    delay = data.get('delay', 120)
    messages = data.get('messages')
    prefix = data.get('prefix', '')
    e2ee_pin = data.get('e2ee_pin', '')
    
    is_running = True
    live_logs = ["[SYSTEM] Thread Loop Started Successfully."]
    
    loop_thread = threading.Thread(target=send_e2ee_loop, args=(cookies, target_id, delay, messages, prefix, e2ee_pin))
    loop_thread.daemon = True
    loop_thread.start()
    
    return jsonify({"status": "Started"})

@app.route('/api/logs')
def get_logs():
    return jsonify(live_logs)

@app.route('/api/stop', methods=['POST'])
def stop_task():
    global is_running
    is_running = False
    return jsonify({"status": "Stopped"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
