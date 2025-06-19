import os
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client

from db import Subscriber, Admin, SessionLocal, init_db, seed_admins_from_env
# Load env
load_dotenv()
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
# admin_numbers = set(os.getenv("ADMIN_NUMBERS", "").split(","))
client = Client(account_sid, auth_token)
app = FastAPI()
# start up functions
init_db()
seed_admins_from_env()

# --- db functions ----
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

def is_admin(phone: str) -> bool:
    db = SessionLocal()
    exists = db.query(Admin).filter_by(phone_number=phone).first()
    db.close()
    return exists is not None

def get_admin_state(phone: str) -> str:
    db = SessionLocal()
    admin = db.query(Admin).filter_by(phone_number=phone).first()
    db.close()
    return admin.state if admin else "unknown"

def set_admin_state(phone: str, new_state: str):
    db = SessionLocal()
    admin = db.query(Admin).filter_by(phone_number=phone).first()
    if admin:
        admin.state = new_state
        db.commit()
    db.close()


class Alert(BaseModel):
    message: str

# api routes
@app.api_route("/inbound-sms", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    if request.method == "POST":
        form = await request.form()
    else:
        form = request.query_params

    sender = form.get("From")
    text = form.get("Body", "").strip().lower()

    if is_admin(sender):
        state = get_admin_state(sender)
        if state == "awaiting_alert":
            subscribers = get_all_subscribers()
            alert =  form.get("Body", "")
            for number in subscribers:
                client.messages.create(
                    to=number,
                    from_=twilio_number,
                    body=f"🏕️📢 Camp Alert! \n {alert}"
                )
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="✅ Alert sent to all subscribers."
            )
            set_admin_state(sender, "idle")

        elif text.lower() == "send out alert":
            set_admin_state(sender, "awaiting_alert")
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="👋 What message would you like to send out?"
            )
        else:
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="⚠️ Unknown command. Text 'send out alert' to begin."
            )
    else:
        if text == "stop":
            remove_subscriber(sender)
            # client.messages.create(
            #     to=sender,
            #     from_=twilio_number,
            #     body="You've been unsubscribed."
            # )
        elif text == "join" or text == "unstop":
            add_subscriber(sender)
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="🏕️ Welcome to Listen CI Camp Alerts! You’re all set. ✅ Text STOP anytime to unsubscribe."
            )
        else:
            client.messages.create(
                    to=sender,
                    from_=twilio_number,
                    body="⚠️ Unrecognized command."
                )
    return {"status": "message sent"}
