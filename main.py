from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os, json
import vonage

# Load env
load_dotenv()
api_key = os.getenv("VONAGE_API_KEY")
api_secret = os.getenv("VONAGE_API_SECRET")
brand_name = os.getenv("VONAGE_BRAND_NAME")

client = vonage.Client(key=api_key, secret=api_secret)
sms = vonage.Sms(client)
app = FastAPI()

# File-based storage
SUBSCRIBERS_FILE = "subscribers.json"
OPT_OUT_FILE = "opt_out.json"

# Helpers
def load_list(path):
    try:
        with open(path, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_list(data, path):
    with open(path, "w") as f:
        json.dump(list(data), f)

# Load existing data
subscribers = load_list(SUBSCRIBERS_FILE)
opt_out = load_list(OPT_OUT_FILE)

class Alert(BaseModel):
    message: str

@app.post("/send-alert")
def send_alert(alert: Alert):
    for number in subscribers:
        if number not in opt_out:
            sms.send_message({
                "from": brand_name,
                "to": number,
                "text": alert.message
            })
    return {"status": "Alert sent to subscribers"}

@app.post("/inbound-sms")
async def inbound_sms(request: Request):
    form = await request.form()
    sender = form.get("msisdn")  # phone number
    text = form.get("text", "").strip().lower()

    if text == "stop":
        opt_out.add(sender)
        save_list(opt_out, OPT_OUT_FILE)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "You’ve been unsubscribed. Reply START to rejoin."
        })

    elif text == "start":
        opt_out.discard(sender)
        subscribers.add(sender)
        save_list(opt_out, OPT_OUT_FILE)
        save_list(subscribers, SUBSCRIBERS_FILE)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "Welcome back to Camp Alerts!"
        })

    elif text == "join":
        if sender in opt_out:
            opt_out.discard(sender)
        subscribers.add(sender)
        save_list(subscribers, SUBSCRIBERS_FILE)
        save_list(opt_out, OPT_OUT_FILE)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "🎉 You’ve joined Camp Alerts! Text STOP to unsubscribe."
        })

    else:
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "Unrecognized command. Text JOIN to subscribe or STOP to unsubscribe."
        })

    return "OK"
