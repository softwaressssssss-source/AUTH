from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

ADMIN_USERNAME = "FR"
ADMIN_PASSWORD = "CONSOLE"

JSONBIN_API_KEY = "$2a$10$R74G8pPzaRy0kLrcmfIYO.jvMl0T8JA3XQVaRHQNqYWsyO8ltxLr."
BIN_ID = "68fef44843b1c97be983b559"

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY
}

# -------------------- TIMEZONE FIX (IST) --------------------

def ist_now():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

# -------------------- EXPIRY LOGIC --------------------

def parse_expiry(expiry_str):
    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(expiry_str, fmt)
        except:
            pass

    return None


def is_expired(expiry_str):
    expiry = parse_expiry(expiry_str)
    if not expiry:
        return False

    return ist_now() > expiry

# -------------------- JSONBIN --------------------

def load_data_raw():
    try:
        res = requests.get(
            f"https://api.jsonbin.io/v3/b/{BIN_ID}?meta=false",
            headers=HEADERS
        )

        if res.status_code == 200:
            return res.json()

        print("LOAD FAILED:", res.status_code, res.text)
        return {}

    except Exception as e:
        print("LOAD ERROR:", e)
        return {}


def save_data(data):
    try:
        res = requests.put(
            f"https://api.jsonbin.io/v3/b/{BIN_ID}?meta=false",
            headers=HEADERS,
            json=data
        )

        print("SAVE STATUS:", res.status_code)
        return res.status_code == 200

    except Exception as e:
        print("SAVE ERROR:", e)
        return False


def clean_expired_users(data):
    changed = False
    now = ist_now()

    for category in list(data.keys()):

        valid_users = []

        for user in data.get(category, []):

            expiry = parse_expiry(user.get("Expiry", ""))

            if expiry and now > expiry:
                print("AUTO DELETE:", user.get("Username"))
                changed = True
                continue

            valid_users.append(user)

        data[category] = valid_users

    if changed:
        save_data(data)

    return data


def load_data():
    data = load_data_raw()
    return clean_expired_users(data)

# -------------------- AUTH --------------------
# -------------------- AUTH --------------------

@app.route('/verify_password', methods=['POST'])
def verify_password():

    password = request.form.get('password')

    if password == "0512":          # ← apna password
        session['verified'] = True
        return jsonify(status="success")

    return jsonify(status="fail")
@app.route("/")
def home():
    if session.get("logged_in"):
        return render_template("index.html")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # 🔑 License Login
        if request.form.get("license_key"):

            key = request.form.get("license_key")
            data = load_data()

            # check all categories
            if "licenses" in data:
                for category in data["licenses"]:
                    for lic in data["licenses"][category]:

                        if lic["Key"] == key:

                            if is_expired(lic["Expiry"]):
                                data["licenses"][category].remove(lic)
                                save_data(data)
                                return render_template("login.html", error="Key expired")

                            if lic["Status"] != "Active":
                                return render_template("login.html", error="Key paused")

                            session["logged_in"] = True
                            return redirect(url_for("home"))

            return render_template("login.html", error="Key not found")

        # 👤 Username Login
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")
import os

from flask import Response
import os

@app.route("/view/<path:filename>")
def view_file(filename):

    if not session.get("verified"):
        return "Unauthorized", 403

    file_path = os.path.join("static", filename)

    if not os.path.exists(file_path):
        return "File not found", 404

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    html = f"""
    <html>
    <head>
        <title>{filename}</title>
        <style>
            body {{
                background:black;
                color:white;
                font-family: monospace;
                padding:20px;
            }}
            pre {{
                background:#050505;
                border:1px solid #222;
                padding:15px;
                white-space: pre-wrap;
            }}
            .topbar {{
                margin-bottom:15px;
            }}
            button {{
                background:red;
                color:white;
                border:none;
                padding:8px 14px;
                margin-right:10px;
                cursor:pointer;
            }}
        </style>
    </head>
    <body>

        <div class="topbar">
            <button onclick="copyText()">📋 Copy</button>
            <a href="/static/{filename}" download>
                <button>⬇ Download</button>
            </a>
        </div>

        <pre id="code">{content}</pre>

        <script>
            function copyText() {{
                const text = document.getElementById("code").innerText;
                navigator.clipboard.writeText(text);
                alert("Copied");
            }}
        </script>

    </body>
    </html>
    """

    return Response(html, mimetype="text/html")



@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))
import secrets
import string

def generate_license_key():
    chars = string.ascii_uppercase + string.digits
    return "-".join(
        ''.join(secrets.choice(chars) for _ in range(4))
        for _ in range(4)
    )
# -------------------- USER MANAGEMENT --------------------
@app.route("/generate_license", methods=["POST"])
def generate_license():
    data = load_data()

    category = request.form["category"]
    expiry = request.form["expiry"]

    if category not in data:
        data[category] = []

    # Ensure licenses list
    if "licenses" not in data:
        data["licenses"] = {}

    if category not in data["licenses"]:
        data["licenses"][category] = []

    key = generate_license_key()

    data["licenses"][category].append({
        "Key": key,
        "HWID": "",
        "Status": "Active",
        "Expiry": expiry,
        "CreatedAt": ist_now().strftime("%Y-%m-%d %H:%M")
    })

    if save_data(data):
        return jsonify({"status": "success", "message": f"Key Created: {key}"})

    return jsonify({"status": "error", "message": "Generation failed"})
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
        "HWID": "",
        "Status": "Active",
        "Expiry": expiry,
        "CreatedAt": ist_now().strftime("%Y-%m-%d %H:%M")
    })

    if save_data(data):
        return jsonify({"status": "success", "message": "User added successfully"})

    return jsonify({"status": "error", "message": "Add failed"})

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

@app.route("/delete_user", methods=["POST"])
def delete_user():
    data = load_data()

    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    before = len(data[category])
    data[category] = [u for u in data[category] if u["Username"] != username]

    if len(data[category]) == before:
        return jsonify({"status": "error", "message": "User not found"})

    if save_data(data):
        return jsonify({"status": "success", "message": "User deleted"})

    return jsonify({"status": "error", "message": "Delete failed"})
    @app.route("/update_license", methods=["POST"])
def update_license():
    data = load_data()

    category = request.form["category"]
    key = request.form["key"]
    action = request.form["action"]

    if "licenses" not in data or category not in data["licenses"]:
        return jsonify({"status": "error", "message": "No licenses"})

    for lic in data["licenses"][category]:

        if lic["Key"] == key:

            if action == "pause":
                lic["Status"] = "Paused"

            elif action == "unpause":
                lic["Status"] = "Active"

            elif action == "delete":
                data["licenses"][category].remove(lic)

            if save_data(data):
                return jsonify({"status": "success", "message": f"License {action}d"})

    return jsonify({"status": "error", "message": "License not found"})
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

            if action == "pause":
                user["Status"] = "Paused"
            else:
                user["Status"] = "Active"

            if save_data(data):
                return jsonify({"status": "success", "message": f"User {action}d"})

            return jsonify({"status": "error", "message": "Save failed"})

    return jsonify({"status": "error", "message": "User not found"})
@app.route("/update_message_status", methods=["POST"])
def update_message_status():
    data = load_data()

    category = request.form["category"]
    username = request.form["username"]
    index = int(request.form["index"])
    action = request.form["action"]

    if category not in data:
        return jsonify({"status": "error", "message": "Invalid application"})

    for user in data[category]:
        if user["Username"] == username:

            if "Messages" not in user:
                return jsonify({"status": "error", "message": "No messages"})

            if index >= len(user["Messages"]):
                return jsonify({"status": "error", "message": "Invalid index"})

            if action == "delete":
                user["Messages"].pop(index)
            else:
                user["Messages"][index]["status"] = action

            if save_data(data):
                return jsonify({"status": "success"})

            return jsonify({"status": "error", "message": "Save failed"})

    return jsonify({"status": "error", "message": "User not found"})
@app.route("/get_licenses", methods=["POST"])
def get_licenses():
    data = load_data()
    category = request.form["category"]

    if "licenses" not in data or category not in data["licenses"]:
        return jsonify([])

    return jsonify(data["licenses"][category])

@app.route("/get_users", methods=["POST"])
def get_users():
    data = load_data()
    return jsonify(data.get(request.form["category"], []))

@app.route("/license_login", methods=["POST"])
def license_login():
    data = load_data()

    category = request.form["category"]
    key = request.form["license_key"]
    hwid = request.form["hwid"]

    if "licenses" not in data or category not in data["licenses"]:
        return jsonify({"status": "error", "message": "Invalid application"})

    for lic in data["licenses"][category]:

        if lic["Key"] == key:

            if is_expired(lic["Expiry"]):
                data["licenses"][category].remove(lic)
                save_data(data)
                return jsonify({"status": "error", "message": "Key expired"})

            if lic["Status"] != "Active":
                return jsonify({"status": "error", "message": "Key paused"})

            if not lic["HWID"]:
                lic["HWID"] = hwid
                save_data(data)
                return jsonify({"status": "success", "message": "HWID bound"})

            if lic["HWID"] != hwid:
                return jsonify({"status": "error", "message": "HWID mismatch"})

            return jsonify({"status": "success", "message": "Login success"})

    return jsonify({"status": "error", "message": "Key not found"})
@app.route("/client_login", methods=["POST"])
def client_login():
    data = load_data()

    category = request.form["category"]
    username = request.form["username"]
    password = request.form["password"]
    hwid = request.form["hwid"]

    if category not in data:
        return jsonify({"status": "error", "message": "Application not found"})

    for user in data[category]:

        if user["Username"].lower() == username.lower():

            if user["Password"].lower() != password.lower():
                return jsonify({"status": "error", "message": "Wrong password"})

            if is_expired(user["Expiry"]):
                data[category] = [u for u in data[category] if u["Username"] != user["Username"]]
                save_data(data)
                return jsonify({"status": "error", "message": "Account expired"})

            if user["Status"] != "Active":
                return jsonify({"status": "error", "message": "Account paused"})

            if not user["HWID"]:
                user["HWID"] = hwid
                save_data(data)

                return jsonify({
                    "status": "success",
                    "message": "HWID bound. Login success",
                    "expiry": user["Expiry"]
                })

            if user["HWID"] != hwid:
                return jsonify({"status": "error", "message": "HWID mismatch"})

            return jsonify({
                "status": "success",
                "message": "Login success",
                "expiry": user["Expiry"]
            })

    return jsonify({"status": "error", "message": "Username does not exist"})

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
                return jsonify({"status": "success", "message": "HWID reset"})

            return jsonify({"status": "error", "message": "Save failed"})

    return jsonify({"status": "error", "message": "User not found"})


# ✅ FIXED ROUTE (ONLY CHANGE)
@app.route("/send_message", methods=["POST"])
def send_message():
    data = load_data()
    username = request.form["username"]
    message = request.form["message"]
    now = ist_now().strftime("%Y-%m-%d %H:%M")

    for category, users in data.items():
        for user in users:
            if user["Username"] == username:

                if "Messages" not in user:
                    user["Messages"] = []

                user["Messages"].append({
                    "text": message,
                    "time": now,
                    "status": "active"
                })

                if save_data(data):
                    return jsonify({"status": "success", "message": "Message saved"})

                return jsonify({"status": "error", "message": "Save failed"})

    return jsonify({"status": "error", "message": "User not found"})


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


# -------------------- RUN --------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
