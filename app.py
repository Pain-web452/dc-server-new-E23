from flask import Flask, render_template, request, jsonify
import time
import threading
import os
from playwright.sync_api import sync_playwright

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

def send_message_via_playwright(cookies_raw, target_id, delay, messages, prefix):
    global is_running
    
    cookie_list = [c.strip() for c in cookies_raw.split('\n') if c.strip()]
    message_list = [m.strip() for m in messages.split('\n') if m.strip()]
    
    if not cookie_list or not message_list:
        add_log("SYSTEM ERROR", "कुकीज़ या मैसेज लिस्ट खाली है।")
        is_running = False
        return

    cookie_index = 0
    message_index = 0
    
    try:
        with sync_playwright() as p:
            # बिना स्क्रीन के बैकएंड में ब्राउज़र शुरू करना
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            
            # यूजर एजेंट सेट करना ताकि फेसबुक ब्लॉक न करे
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # सबसे पहले फेसबुक डोमेन ओपन करना
            page.goto("https://facebook.com")
            page.wait_for_timeout(2000)
            
            while is_running:
                current_cookie = cookie_list[cookie_index]
                
                # c_user=...; xs=... को प्लेराइट फॉर्मेट में बदलना और लोड करना
                pairs = current_cookie.split(';')
                playwright_cookies = []
                for pair in pairs:
                    if '=' in pair:
                        name, value = pair.split('=', 1)
                        playwright_cookies.append({
                            'name': name.strip(),
                            'value': value.strip(),
                            'domain': '.facebook.com',
                            'path': '/'
                        })
                context.add_cookies(playwright_cookies)
                
                base_message = message_list[message_index]
                final_message = f"{prefix} {base_message}" if prefix else base_message
                
                # डायरेक्ट पर्सनल इनबॉक्स चैट लिंक पर जाना
                message_url = f"https://facebook.com/messages/thread/{target_id}"
                page.goto(message_url)
                page.wait_for_timeout(3000)
                
                try:
                    # मैसेज इनपुट बॉक्स (NAME: body) ढूंढना और टाइप करना
                    page.fill("textarea[name='body']", final_message)
                    
                    # सेंड बटन (NAME: send) पर क्लिक करना
                    page.click("input[name='send']")
                    page.wait_for_timeout(2000)
                    
                    log_prefix = prefix if prefix else "MESSENGER BOT"
                    add_log(log_prefix, final_message)
                    
                except Exception as e:
                    if "login" in page.url or "checkpoint" in page.url:
                        add_log("SYSTEM ERROR", f"कुकी नंबर {cookie_index + 1} एक्सपायर या ब्लॉक हो चुकी है।")
                    else:
                        add_log("ERROR", f"मैसेज फेल: {str(e)}")
                
                # अगले मैसेज और अगली कुकी पर जाना
                cookie_index = (cookie_index + 1) % len(cookie_list)
                message_index = (message_index + 1) % len(message_list)
                
                time.sleep(int(delay))
                
            browser.close()
            
    except Exception as main_e:
        add_log("CRITICAL ERROR", f"सिस्टम क्रैश हुआ: {str(main_e)}")
    finally:
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
    delay = data.get('delay', 30)
    messages = data.get('messages')
    prefix = data.get('prefix', '')
    
    is_running = True
    live_logs = ["[SYSTEM] Render सर्वर पर ब्राउज़र ऑटोमेशन शुरू हो रहा है..."]
    
    loop_thread = threading.Thread(target=send_message_via_playwright, args=(cookies, target_id, delay, messages, prefix))
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
    
