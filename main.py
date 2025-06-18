import os
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from db import Subscriber, SessionLocal, init_db
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client

# Load env
load_dotenv()
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
admin_numbers = set(os.getenv("ADMIN_NUMBERS", "").split(","))
client = Client(account_sid, auth_token)
app = FastAPI()
init_db()

# should integrate into db 
admin_state = {}

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

# @app.post("/send-alert")
# def send_alert(alert: Alert):
#     subscribers = get_all_subscribers() 
#     print(alert)
#     for number in subscribers:
#         print(f"Sending to {number}")
#         client.messages.create(
#             body=alert.message,
#             from_=twilio_number,
#             to=number
#         )
#     return {"status": "Alert sent to campers"}


@app.api_route("/inbound-sms", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    if request.method == "POST":
        form = await request.form()
    else:
        form = request.query_params

    sender = form.get("From")
    text = form.get("Body", "").strip().lower()

    if text == "stop":
        remove_subscriber(sender)
        # resp.message("You've been unsubscribed.")
        client.messages.create(
            to=sender,
            from_=twilio_number,
            body="You've been unsubscribed."
        )
    elif text == "join":
        add_subscriber(sender)
        # resp.message("You've joined Camp Alerts!!")
        client.messages.create(
            to=sender,
            from_=twilio_number,
            body="You've joined Camp Alerts!!"
        )


    # Check if sender is admin
    if sender in admin_numbers:
        if admin_state.get(sender) == "awaiting_alert":
            subscribers = get_all_subscribers()
            for number in subscribers:
                client.messages.create(
                    to=number,
                    from_=twilio_number,
                    body=f"Camp Alert: {text}"
                )
            # resp.message("✅ Alert sent to all subscribers.")
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="✅ Alert sent to all subscribers."
            )
            admin_state.pop(sender)  # Reset state
        elif text.lower() == "send out alert":
            admin_state[sender] = "awaiting_alert"
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="👋 Welcome Admin. What would you like me to send out?"
            )
            # resp.message("👋 Welcome Admin. What would you like me to send out?")
        else:
            client.messages.create(
                to=sender,
                from_=twilio_number,
                body="⚠️ Unrecognized command. Text 'send out alert' to begin."
            )
            # resp.message("⚠️ Unrecognized command. Text 'send out alert' to begin.")

    else:
        client.messages.create(
                to=sender,
                from_=twilio_number,
                body="⚠️ Unrecognized command. Text 'send out alert' to begin."
            )
        # resp.message("🤖 Unrecognized command. Text JOIN to subscribe or STOP to unsubscribe.")

    return {"status": "message sent"}
