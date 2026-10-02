from flask import Flask, render_template, request, jsonify
import time
import threading
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

is_running = False
live_logs = []
loop_thread = None

def add_log(prefix_tag, text):
    time_now = time.strftime("%H:%M:%S")
    log_entry = f"<span style='color:#ff007f;'>{prefix_tag}</span><br>[{time_now}] ✅ Sent:<br>\"{text}\"<br>-----------------------"
    live_logs.append(log_entry)
    if len(live_logs) > 50:
        live_logs.pop(0)

def inject_cookies_to_browser(driver, raw_cookies):
    # c_user=123; xs=abc फॉर्मेट से कुकीज निकालकर ब्राउज़र में सेट करना
    pairs = raw_cookies.split(';')
    for pair in pairs:
        if '=' in pair:
            name, value = pair.split('=', 1)
            driver.add_cookie({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.facebook.com',
                'path': '/'
            })

def send_message_via_selenium(cookies_raw, target_id, delay, messages, prefix):
    global is_running
    
    cookie_list = [c.strip() for c in cookies_raw.split('\n') if c.strip()]
    message_list = [m.strip() for m in messages.split('\n') if m.strip()]
    
    if not cookie_list or not message_list:
        add_log("SYSTEM ERROR", "कुकीज़ या मैसेज लिस्ट खाली है।")
        is_running = False
        return

    # Render एनवायरनमेंट के लिए Chrome बाइनरी सेट करना
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Render पर Buildpack द्वारा इंस्टॉल किए गए Chrome का पाथ
    options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/chrome"

    # Chromium Driver पाथ सेट करना
    chrome_driver_path = "/opt/render/project/.render/chromedriver/chromedriver"
    
    try:
        service = Service(executable_path=chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        add_log("DRV ERROR", f"ड्राइवर इनिशियलाइज़ेशन फेल: {str(e)}")
        is_running = False
        return
    
    cookie_index = 0
    message_index = 0
    
    try:
        # फेसबुक पर जाकर कुकी इंजेक्ट करना
        driver.get("https://facebook.com")
        time.sleep(2)
        
        while is_running:
            # हर लूप में वर्तमान कुकी डालना (अगर मल्टीपल कुकीज़ हैं)
            current_cookie = cookie_list[cookie_index]
            inject_cookies_to_browser(driver, current_cookie)
            
            base_message = message_list[message_index]
            final_message = f"{prefix} {base_message}" if prefix else base_message
            
            message_url = f"https://facebook.com/messages/thread/{target_id}"
            driver.get(message_url)
            time.sleep(3)
            
            try:
                # मैसेज इनपुट बॉक्स और सेंड बटन को संभालना
                message_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "body"))
                )
                message_box.clear()
                message_box.send_keys(final_message)
                
                send_button = driver.find_element(By.NAME, "send")
                send_button.click()
                
                log_prefix = prefix if prefix else "MESSENGER BOT"
                add_log(log_prefix, final_message)
                
            except Exception as e:
                if "login" in driver.current_url or "checkpoint" in driver.current_url:
                    add_log("SYSTEM ERROR", f"कुकी नंबर {cookie_index + 1} एक्सपायर हो चुकी है या ब्लॉक है।")
                else:
                    add_log("ERROR", f"मैसेज भेजने में विफलता: {str(e)}")
            
            # अगले मैसेज और अगली कुकी पर शिफ्ट होना
            cookie_index = (cookie_index + 1) % len(cookie_list)
            message_index = (message_index + 1) % len(message_list)
            
            time.sleep(int(delay))
            
    except Exception as main_e:
        add_log("CRITICAL ERROR", f"सिस्टम क्रैश: {str(main_e)}")
    finally:
        driver.quit()
        is_running = False
        add_log("SYSTEM", "बॉट प्रक्रिया बंद हो गई है।")

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
    delay = data.get('delay', 10)
    messages = data.get('messages')
    prefix = data.get('prefix', '')
    
    is_running = True
    live_logs = ["[SYSTEM] Render सर्वर पर Selenium चालू हो रहा है... कृपया प्रतीक्षा करें।"]
    
    loop_thread = threading.Thread(target=send_message_via_selenium, args=(cookies, target_id, delay, messages, prefix))
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
