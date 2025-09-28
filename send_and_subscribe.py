import os
import json
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

SUBSCRIBERS_FILE = "subscribers.json"
OFFSET_FILE = "offset.txt"
SCHEDULE_FILE = "schedule.json"
SENT_FILE = "sent_recent.json"  # Хранит id сообщений, отправленных за последние 15 минут

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
    sent_recent = load_json(SENT_FILE, [])
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
                subscribers = [s for s in subscribers if s["chat_id"] != chat_id]
                send_message(chat_id, "❌ Подписка отменена. Больше уведомлений не будет.")

    # Проверка расписания с окном 15 минут
    now = datetime.utcnow()
    window = timedelta(minutes=15)

    for item in schedule:
        msg_time_str = item.get("time")
        if not msg_time_str:
            continue

        # Проверяем все даты (одна дата или список)
        dates_to_check = []
        if "date" in item:
            dates_to_check.append(item["date"])
        if "dates" in item:
            dates_to_check.extend(item["dates"])

        for d in dates_to_check:
            msg_datetime = datetime.strptime(f"{d} {msg_time_str}", "%Y-%m-%d %H:%M")
            # Если текущее время в пределах окна 15 минут и сообщение ещё не отправлено
            if msg_datetime <= now <= msg_datetime + window and item["id"] not in sent_recent:
                for sub in subscribers:
                    send_message(sub["chat_id"], item["text"])
                sent_recent.append(item["id"])

    # Сохраняем данные
    save_json(SUBSCRIBERS_FILE, subscribers)
    save_json(SENT_FILE, sent_recent)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

if __name__ == "__main__":
    main()