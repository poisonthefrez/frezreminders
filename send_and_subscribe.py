import os
import json
import requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

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

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_updates(offset):
    r = requests.get(f"{API_URL}/getUpdates", params={"offset": offset+1, "timeout":10})
    return r.json()

def main():
    subscribers = load_json(SUBSCRIBERS_FILE, [])
    schedule = load_json(SCHEDULE_FILE, [])
    offset = 0
    if os.path.exists(OFFSET_FILE):
        try:
            offset = int(open(OFFSET_FILE).read().strip())
        except:
            offset = 0

    # Обработка новых подписчиков
    updates = get_updates(offset)
    if updates.get("result"):
        for upd in updates["result"]:
            offset = upd["update_id"]
            msg = upd.get("message") or {}
            text = msg.get("text","")
            chat_id = msg.get("chat",{}).get("id")
            if text.lower() == "/start" and chat_id:
                if chat_id not in [s["chat_id"] for s in subscribers]:
                    subscribers.append({"chat_id": chat_id, "welcome_sent": True})
                    send_message(chat_id, "✅ Подписка оформлена!")
            elif text.lower() == "/stop" and chat_id:
                if chat_id in subscribers:
                    subscribers.remove(chat_id)
                    send_message(chat_id, "❌ Подписка отменена. Больше уведомлений не будет.")

    # Проверка расписания
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    day_of_week = now.strftime("%a")  # Mon, Tue, ...

    for item in schedule:
        msg_time = item.get("time")
        if not msg_time:
            continue

        should_send = False

        # одноразовая дата
        if "date" in item and item["date"] == today_str and msg_time == time_str:
            should_send = True

        # список дат
        if "dates" in item and today_str in item["dates"] and msg_time == time_str:
            should_send = True

        # дни недели
        if "days" in item and day_of_week in item["days"] and msg_time == time_str:
            should_send = True

        if should_send:
            for chat_id in subscribers:
                send_message(chat_id, item["text"])

    # Сохраняем данные
    save_json(SUBSCRIBERS_FILE, subscribers)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

if __name__ == "__main__":
    main()