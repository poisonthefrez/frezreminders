import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# --- TIMEZONE ---
MSK = timezone(timedelta(hours=3))  # Moscow = UTC+2

# --- FILES ---
SUBSCRIBERS_FILE = "subscribers.json"
OFFSET_FILE = "offset.txt"
SCHEDULE_FILE = "schedule.json"


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- BOT METHODS ---
def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


def get_updates(offset):
    url = f"{API_URL}/getUpdates"
    r = requests.get(url, params={"offset": offset, "timeout": 10})
    return r.json()


# --- MAIN ---
def main():
    subscribers = load_json(SUBSCRIBERS_FILE, [])
    schedule = load_json(SCHEDULE_FILE, [])
    offset = 0
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f:
            try:
                offset = int(f.read().strip())
            except:
                offset = 0

    # 1. Обрабатываем новые команды
    updates = get_updates(offset + 1)
    if updates.get("result"):
        for upd in updates["result"]:
            offset = upd["update_id"]
            if "message" in upd and "text" in upd["message"]:
                text = upd["message"]["text"]
                chat_id = upd["message"]["chat"]["id"]
                if text.lower() == "/start":
                    if chat_id not in subscribers:
                        subscribers.append(chat_id)
                        send_message(chat_id, "✅ Подписка оформлена! Теперь ты получаешь напоминания.")
                elif text.lower() == "/stop":
                    if chat_id in subscribers:
                        subscribers.remove(chat_id)
                        send_message(chat_id, "❌ Подписка отменена. Больше не получаешь напоминания.")

    # 2. Проверяем расписание
    now = datetime.now(MSK)
    today_str = now.strftime("%Y-%m-%d")
    day_of_week = now.strftime("%a")  # Mon, Tue, ...
    current_time = now.strftime("%H:%M")

    for item in schedule:
        msg_time = item.get("time")
        if not msg_time:
            continue

        should_send = False

        # --- одноразовая дата ---
        if "date" in item and item["date"] == today_str and msg_time == current_time:
            should_send = True

        # --- список дат ---
        if "dates" in item and today_str in item["dates"] and msg_time == current_time:
            should_send = True

        # --- дни недели ---
        if "days" in item and day_of_week in item["days"] and msg_time == current_time:
            should_send = True

        if should_send:
            for chat_id in subscribers:
                send_message(chat_id, item["text"])

    # 3. Сохраняем оффсет и подписчиков
    save_json(SUBSCRIBERS_FILE, subscribers)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


if __name__ == "__main__":
    main()