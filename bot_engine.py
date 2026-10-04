import asyncio
import threading
import datetime
import os
from fbchat_muqit import Client, ThreadType

bot_state = {"status": "Stopped", "client": None, "thread": None}
logs = []


def add_log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    logs.append(f"[BOT] [{ts}] {msg}")
    if len(logs) > 300:
        logs.pop(0)


def get_logs():
    return logs


def clear_logs():
    logs.clear()


def load_message():
    if not os.path.exists("message.txt"):
        return None
    try:
        with open("message.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


async def send_loop(client, group_id, interval):
    await asyncio.sleep(10)
    while bot_state["status"] == "Running":
        try:
            msg = load_message()
            if msg:
                await client.send_message(msg, group_id)
                add_log(f"✅ Message bheja ({len(msg)} chars)")
            else:
                add_log("⚠️ Message file khali hai")
        except Exception as e:
            add_log(f"❌ Send error: {e}")
        await asyncio.sleep(interval)


async def bot_main(group_id, interval):
    add_log("INFO: ✅ Dashboard client connected")
    add_log("Bot status: Started")

    client = Client(cookies_file_path="cookies.json")

    @client.event
    async def on_ready():
        add_log(f"✅ Bot logged in as UID: {client.uid}")
        add_log(f"📨 Target Group: {group_id}")
        add_log(f"⏰ Interval: {interval} seconds")
        asyncio.create_task(send_loop(client, group_id, interval))

    @client.event
    async def on_message(message):
        if message.sender_id == client.uid:
            return
        if not message.text:
            return
        text = message.text.strip().lower()
        if text == "/tid":
            await client.send_message(f"Group ID: {message.thread_id}", message.thread_id)
        elif text == "/ping":
            await client.send_message("🏓 Pong! Bot active.", message.thread_id)

    bot_state["client"] = client
    bot_state["status"] = "Running"

    try:
        client.run()
    except Exception as e:
        add_log(f"ERROR: {e}")
        bot_state["status"] = "Stopped"


def run_bot_thread(group_id, interval):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main(group_id, interval))
    except Exception as e:
        add_log(f"ERROR in thread: {e}")


def start_bot(group_id, interval):
    if bot_state["status"] == "Running":
        return {"status": "already_running", "message": "Bot already chal raha hai"}
    thread = threading.Thread(target=run_bot_thread, args=(group_id, interval), daemon=True)
    thread.start()
    bot_state["thread"] = thread
    return {"status": "started", "message": "Bot start ho gaya"}


def stop_bot():
    bot_state["status"] = "Stopped"
    bot_state["client"] = None
    add_log("Bot stopped by user")
    return {"status": "stopped", "message": "Bot band ho gaya"}
