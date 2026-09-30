from flask import Flask, render_template, request, jsonify, redirect
import threading
import requests
import time
import re
import os

app = Flask(__name__)

bot_status = {
    "running": False,
    "logs": ["Waiting for task to launch... Connected to Render Server."],
    "render_url": "" # Render app link auto detect karega
}

def self_ping_loop():
    """Render Server ko sone (sleep) se bachane ke liye automatic pinger"""
    time.sleep(30)
    while True:
        if bot_status["render_url"]:
            try:
                requests.get(bot_status["render_url"], timeout=10)
                print("[Render Keep-Alive] Self-ping done successfully.", flush=True)
            except Exception:
                pass
        time.sleep(600) # Har 10 minute me ping karega

def get_fb_dtsg(session, uid, cookie):
    headers = {
        "cookie": cookie,
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    }
    chat_url = f"https://facebook.com.{uid}%3A"
    try:
        res = session.get(chat_url, headers=headers, timeout=12)
        if res.status_code == 200:
            dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', res.text)
            action_match = re.search(r'action="(/messages/send/\?.*?)"', res.text)
            if dtsg_match and action_match:
                return dtsg_match.group(1), f"https://facebook.com{action_match.group(1)}"
    except Exception as e:
        bot_status["logs"].append(f"❌ Token Extraction Error: {str(e)}")
    return None, None

def start_messaging_loop(cookie, thread_id, prefix, messages, delay):
    global bot_status
    bot_status["running"] = True
    bot_status["logs"] = ["🚀 SYSTEM AUTOMATION STARTED ON RENDER SERVER..."]
    
    session = requests.Session()
    headers = {
        "cookie": cookie,
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    }

    for idx, msg in enumerate(messages):
        if not bot_status["running"]:
            break
            
        msg = msg.strip()
        if not msg:
            continue

        fb_dtsg, send_url = get_fb_dtsg(session, thread_id, cookie)
        
        if not fb_dtsg or not send_url:
            bot_status["logs"].append("❌ Error: Invalid Cookie String! Session Expired.")
            break

        current_time = time.strftime("[%I:%M:%S %p]")
        full_message = f"{prefix} {msg}"
        payload = {"fb_dtsg": fb_dtsg, "body": full_message, "Send": "Send"}

        try:
            res = session.post(send_url, headers=headers, data=payload, timeout=12)
            if res.status_code == 200:
                log_entry = f"{prefix}\n{current_time} ✅ Sent:\n\"{msg}\""
                bot_status["logs"].append(log_entry)
                print(f"[RENDER LOG] {log_entry}", flush=True)
            else:
                bot_status["logs"].append(f"⚠️ Failed. Server Status: {res.status_code}")
        except Exception as e:
            bot_status["logs"].append(f"❌ Transmission Error: {str(e)}")

        if idx < len(messages) - 1 and bot_status["running"]:
            time.sleep(int(delay))

    bot_status["running"] = False
    bot_status["logs"].append("🏁 TASK MONITOR: Task finished or stopped.")

@app.route('/')
def index():
    # Render hosting link dynamically save karna self ping ke liye
    if not bot_status["render_url"]:
        bot_status["render_url"] = request.url_root
    return render_template('index.html')

@app.route('/start-automation', methods=['POST'])
def start_automation():
    cookie = request.form.get('cookieString')
    thread_id = request.form.get('threadId')
    prefix = request.form.get('messagePrefix', '')
    delay = request.form.get('delay', 120)
    file = request.files.get('messageFile')
    
    if file and not bot_status["running"]:
        messages = file.read().decode('utf-8').splitlines()
        t = threading.Thread(target=start_messaging_loop, args=(cookie, thread_id, prefix, messages, delay))
        t.daemon = True
        t.start()
        
    return redirect('/')

@app.route('/stop-automation')
def stop_automation():
    global bot_status
    bot_status["running"] = False
    bot_status["logs"].append("🛑 [STOPPED BY USER] Task force-killed.")
    return redirect('/')

@app.route('/get-logs')
def get_logs():
    return jsonify({"running": bot_status["running"], "logs": bot_status["logs"][-5:]})

if __name__ == '__main__':
    # Keep alive loop ko backend background me trigger karna
    ping_thread = threading.Thread(target=self_ping_loop)
    ping_thread.daemon = True
    ping_thread.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
