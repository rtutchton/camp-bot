import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from db import Subscriber, SessionLocal, init_db
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from fastapi.responses import PlainTextResponse

# Load env
load_dotenv()
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)
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
        print(f"Sending to {number}")
        client.messages.create(
            body=alert.message,
            from_=twilio_number,
            to=number
        )
    return {"status": "Alert sent to campers"}


@app.api_route("/inbound-sms", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    if request.method == "POST":
        form = await request.form()
    else:
        form = request.query_params

    sender = form.get("From")
    text = form.get("Body", "").strip().lower()

    resp = MessagingResponse()

    if text == "stop":
        remove_subscriber(sender)
        resp.message("You’ve been unsubscribed. Reply START to rejoin.")

    elif text == "join":
        add_subscriber(sender)
        resp.message("You’ve joined Camp Alerts! Text STOP to unsubscribe.")

    elif text == "send_message":
        resp.message("Welcome Admin, please tell me what message you want to send out to all camp members.")

    else:
        resp.message("Unrecognized command. Text JOIN to subscribe or STOP to unsubscribe.")

    return PlainTextResponse(str(resp))