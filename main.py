import os
import vonage
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from db import Subscriber, SessionLocal, init_db
from sqlalchemy.exc import IntegrityError

# Load env
load_dotenv()
api_key = os.getenv("VONAGE_API_KEY")
api_secret = os.getenv("VONAGE_API_SECRET")
brand_name = os.getenv("VONAGE_BRAND_NAME")
client = vonage.Client(key=api_key, secret=api_secret)
sms = vonage.Sms(client)
app = FastAPI()
init_db()

SUBSCRIBERS_FILE = "subscribers.json"
OPT_OUT_FILE = "opt_out.json"

# db classes
def add_subscriber(phone: str):
    db = SessionLocal()
    try:
        db.add(Subscriber(phone_number=phone))
        db.commit()
    except IntegrityError:
        db.rollback()  # Already exists
    finally:
        db.close()

def remove_subscriber(phone: str):
    db = SessionLocal()
    db.query(Subscriber).filter(Subscriber.phone_number == phone).delete()
    db.commit()
    db.close()

def get_all_subscribers():
    db = SessionLocal()
    subs = db.query(Subscriber.phone_number).all()
    db.close()
    return [s[0] for s in subs]

class Alert(BaseModel):
    message: str

@app.post("/send-alert")
def send_alert(alert: Alert):
    subscribers = get_all_subscribers() 
    print(alert)
    for number in subscribers:
        print("sending to ", number)
        sms.send_message({
            "from": brand_name,
            "to": number,
            "text": alert.message
        })
    return {"status": "Alert sent to subscribers"}


@app.api_route("/inbound-sms", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    if request.method == "POST":
        form = await request.form()
    else:
        form = request.query_params

    sender = form.get("msisdn")
    text = form.get("text", "").strip().lower()

    if text == "stop":
        remove_subscriber(sender)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "You’ve been unsubscribed. Reply START to rejoin."
        })

    elif text == "join":
        add_subscriber(sender)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "You’ve joined Camp Alerts! Text STOP to unsubscribe."
        })
    
     elif text == "send message":
        # add_subscriber(sender)
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "Welcome Admin, please tell me what message you want to send out to all camp members"
        })

    else:
        sms.send_message({
            "from": brand_name,
            "to": sender,
            "text": "Unrecognized command. Text JOIN to subscribe or STOP to unsubscribe."
        })

    return "OK"
