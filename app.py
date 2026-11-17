import os
import time
import secrets
import threading
import requests
from flask import Flask, request, abort

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = os.environ["OWNER_ID"]
PUBLIC_URL = os.environ["PUBLIC_URL"].rstrip("/")

links = {}

def telegram(method, data=None, files=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, data=data, files=files, timeout=40)

@app.route("/")
def home():
    return "Photo submission service is running."

@app.route("/upload/<token>", methods=["GET", "POST"])
def upload(token):
    if token not in links or links[token] < time.time():
        abort(404)

    if request.method == "POST":
        if request.form.get("consent") != "yes":
            abort(400)

        photo = request.files.get("photo")
        if not photo or not photo.mimetype.startswith("image/"):
            abort(400)

        telegram(
            "sendPhoto",
            data={
                "chat_id": OWNER_ID,
                "caption": "A visitor submitted a photo with consent."
            },
            files={"photo": photo}
        )

        del links[token]
        return "Photo submitted successfully. You can close this page."

    return """
    <h2>Submit a photo</h2>
    <p>Choose a photo to send to the bot owner.</p>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="photo" accept="image/*"
             capture="environment" required>
      <p>
        <label>
          <input type="checkbox" name="consent" value="yes" required>
          I agree to send this photo to the bot owner.
        </label>
      </p>
      <button type="submit">Submit photo</button>
    </form>
    """

def bot_loop():
    offset = 0
    while True:
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35
            ).json()

            for update in response.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "")

                if chat_id == OWNER_ID and text == "/start":
                    telegram("sendMessage", {
                        "chat_id": OWNER_ID,
                        "text": "Welcome! Send /link to create a photo submission link."
                    })

                elif chat_id == OWNER_ID and text == "/link":
                    token = secrets.token_urlsafe(16)
                    links[token] = time.time() + 900
                    telegram("sendMessage", {
                        "chat_id": OWNER_ID,
                        "text": f"Your photo submission link (valid 15 minutes):\n{PUBLIC_URL}/upload/{token}"
                    })

        except Exception:
            time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()