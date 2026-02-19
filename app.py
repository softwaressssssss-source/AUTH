from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import requests
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Admin credentials
ADMIN_USERNAME = "FR"
ADMIN_PASSWORD = "SHUBH"

# JSONBin Config
JSONBIN_API_KEY = "$2a$10$R74G8pPzaRy0kLrcmfIYO.jvMl0T8JA3XQVaRHQNqYWsyO8ltxLr."
BIN_ID = "68fef44843b1c97be983b559"

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY
}

# ---------------------------- Auth Routes ----------------------------

@app.route("/")
def home():
    if session.get("logged_in"):
        return render_template("index.html")
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# ---------------------------- JSONBin Logic ----------------------------

def load_data():
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest", headers=HEADERS)
        if res.status_code == 200:
            return res.json().get("record", {})
        return {}
    except Exception as e:
        print("Load Error:", e)
        return {}

def save_data(data):
    try:
        res = requests.put(f"https://api.jsonbin.io/v3/b/{BIN_ID}", headers=HEADERS, json=data)
        return res.status_code == 200
    except Exception as e:
        print("Save Error:", e)
        return False

# ---------------------------- User Management ----------------------------

@app.route("/add_user", methods=["POST"])
def add_user():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]
    password = request.form["password"]
    expiry = request.form["expiry"]

    if category not in data:
        data[category] = []

    if any(u["Username"] == username for u in data[category]):
        return jsonify({"status": "error", "message": "Username already exists"})

    data[category].append({
        "Username": username,
        "Password": password,
        "HWID": None,
        "Status": "Active",
        "Expiry": expiry,
        "CreatedAt": datetime.today().strftime("%Y-%m-%d")
    })

    if save_data(data):
        return jsonify({"status": "success", "message": "User added successfully"})
    return jsonify({"status": "error", "message": "Failed to add user"})

@app.route("/client_login", methods=["POST"])
def client_login():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]
    password = request.form["password"]
    client_hwid = request.form["hwid"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username and user["Password"] == password:
            if user["Status"] != "Active":
                return jsonify({"status": "error", "message": "Account paused"})

            if user["HWID"] in [None, ""]:
                user["HWID"] = client_hwid
                if save_data(data):
                    return jsonify({"status": "success", "message": "HWID bound. Login success"})
                else:
                    return jsonify({"status": "error", "message": "Failed to bind HWID"})

            if user["HWID"] != client_hwid:
                return jsonify({"status": "error", "message": "HWID mismatch. Access denied"})

            return jsonify({"status": "success", "message": "Login success"})

    return jsonify({"status": "error", "message": "Invalid username or password"})

@app.route("/pause_user", methods=["POST"])
def pause_user():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]
    action = request.form["action"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username:
            user["HWID"] = None if action == "pause" else ""
            user["Status"] = "Paused" if action == "pause" else "Active"
            if save_data(data):
                return jsonify({"status": "success", "message": f"User {action}d"})
            return jsonify({"status": "error", "message": "Failed to update user"})

    return jsonify({"status": "error", "message": "User not found"})

@app.route("/delete_user", methods=["POST"])
def delete_user():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    original_len = len(data[category])
    data[category] = [u for u in data[category] if u["Username"] != username]

    if len(data[category]) == original_len:
        return jsonify({"status": "error", "message": "User not found"})

    if save_data(data):
        return jsonify({"status": "success", "message": "User deleted"})
    return jsonify({"status": "error", "message": "Failed to update data"})

@app.route("/reset_hwid", methods=["POST"])
def reset_hwid():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username:
            user["HWID"] = ""
            if save_data(data):
                return jsonify({"status": "success", "message": f"HWID reset for {username}"})
            return jsonify({"status": "error", "message": "Failed to reset HWID"})

    return jsonify({"status": "error", "message": "User not found"})

@app.route("/info_user", methods=["POST"])
def info_user():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username:
            return jsonify({"status": "success", "data": user})

    return jsonify({"status": "error", "message": "User not found"})

@app.route("/get_users", methods=["POST"])
def get_users():
    data = load_data()
    category = request.form["category"]
    return jsonify(data.get(category, []))

# ---------------------------- Messaging ----------------------------

@app.route("/get_messages", methods=["POST"])
def get_messages():
    data = load_data()
    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username:
            return jsonify({"status": "success", "messages": user.get("Messages", [])})

    return jsonify({"status": "error", "message": "User not found"})

@app.route("/ssend_messaage", methods=["POST"])
def send_message():
    data = load_data()
    username = request.form["username"]
    message = request.form["message"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    found = False

    for category, users in data.items():
        for user in users:
            if user["Username"] == username:
                if "Messages" not in user:
                    user["Messages"] = []
                user["Messages"].append({
                    "text": message,
                    "time": now,
                    "status": "active"  # ✅ Important
                })
                found = True
                break
        if found:
            break

    if not found:
        return jsonify({"status": "error", "message": "User not found"})

    if save_data(data):
        return jsonify({"status": "success", "message": "Message saved"})
    return jsonify({"status": "error", "message": "Failed to save message"})

@app.route("/update_message_status", methods=["POST"])
def update_message_status():
    data = load_data()
    category = request.form["category"].strip().lower()
    username = request.form["username"].strip().lower()
    index = int(request.form["index"])
    action = request.form["action"]

    lowered_data = {k.lower(): v for k, v in data.items()}

    if category not in lowered_data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in lowered_data[category]:
        if user["Username"].lower() == username:
            if "Messages" in user and index < len(user["Messages"]):
                if action == "delete":
                    user["Messages"].pop(index)
                else:
                    user["Messages"][index]["status"] = action
                if save_data(data):
                    return jsonify({"status": "success", "message": f"Message {action}d"})
                return jsonify({"status": "error", "message": "Failed to update message"})
            return jsonify({"status": "error", "message": "Invalid message index"})

    return jsonify({"status": "error", "message": "User not found"})

# ---------------------------- Run ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)