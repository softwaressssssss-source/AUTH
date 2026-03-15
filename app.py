from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
BLOCKED_IPS = [
    "49.37.7.46"
]
LICENSE_KEYS = {
    "SHUBH": {"hwid": ""},
    "HARSH": {"hwid": ""},
    "PRINCE": {"hwid": ""}
}
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1482608417276428403/tbA3o5_q4e46vjHtDrNpn15FsRLFQwYPEv73ib379JpvWcqPaGkcR4YCQcrKz-c3FV4K"
DISCORD_WEBHOOKK = "https://discord.com/api/webhooks/1482608301031297179/9-edWNX_4W1NACFTlLDA2oVlKu875ot3pDb9bDcp9DUZE2VwoCnNUsNykdmgj78kF7Vk"
ADMIN_USERNAME = "FR"
ADMIN_PASSWORD = "PUSSY"

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
def is_online(last_seen):

    if not last_seen:
        return False

    try:
        t = datetime.strptime(last_seen,"%Y-%m-%d %H:%M:%S")
        return (ist_now() - t).seconds < 15
    except:
        return False
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

# ------------------- JSONBIN --------------------

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
    
def send_login_info():
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip:
            ip = ip.split(",")[0].strip()

        user_agent = request.headers.get("User-Agent")

        if "Windows" in user_agent:
            device_name = "Windows PC"
        elif "Android" in user_agent:
            device_name = "Android Phone"
        elif "iPhone" in user_agent:
            device_name = "iPhone"
        elif "Mac" in user_agent:
            device_name = "Mac"
        else:
            device_name = "Unknown Device"

        time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        data = {
            "embeds": [
                {
                    "title": "💻 Login Information",
                    "color": 0x32CD32,
                    "fields": [
                        {"name": "🌐 IP Address", "value": ip, "inline": False},
                        {"name": "🖥 Device", "value": device_name, "inline": False},
                        {"name": "📱 User-Agent", "value": user_agent, "inline": False},
                        {"name": "⏰ Time", "value": time, "inline": False}
                    ],
                    "footer": {
                        "text": "FR Console Security"
                    }
                }
            ]
        }

        requests.post(DISCORD_WEBHOOK, json=data)

    except Exception as e:
        print("Webhook error:", e)

def load_data():
    data = load_data_raw()
    return clean_expired_users(data)
def send_client_login(app_name, username, password, ip, hwid, pc_name):
    try:
        data = {
            "embeds": [
                {
                    "title": "🔐 Client Login",
                    "color": 0x32CD32,
                    "fields": [
                        {"name": "Application", "value": app_name, "inline": False},
                        {"name": "Username", "value": username, "inline": False},
                        {"name": "Password", "value": password, "inline": False},
                        {"name": "IP Address", "value": ip, "inline": False},
                        {"name": "PC Name", "value": pc_name, "inline": False},
                        {"name": "HWID", "value": hwid, "inline": False},
                        {"name": "Time", "value": ist_now().strftime("%Y-%m-%d %H:%M:%S"), "inline": False}
                    ],
                    "footer": {
                        "text": "FR Console Login Log"
                    }
                }
            ]
        }

        requests.post(DISCORD_WEBHOOKK, json=data)

    except Exception as e:
        print("Webhook error:", e)
# -------------------- AUTH --------------------
# -------------------- AUTH --------------------
@app.route("/ping", methods=["POST"])
def ping():

    data = load_data()

    category = request.form["category"]
    username = request.form["username"]

    if category not in data:
        return jsonify({"status":"error"})

    for user in data[category]:

        if user["Username"] == username:

            user["LastSeen"] = ist_now().strftime("%Y-%m-%d %H:%M:%S")
            save_data(data)

            return jsonify({"status":"ok"})

    return jsonify({"status":"error"})
@app.route("/license_login", methods=["POST"])
def license_login():

    license_key = request.form.get("license", "").upper()

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip:
        ip = ip.split(",")[0].strip()

    # 🔴 ADD THIS
    if ip in BLOCKED_IPS:
        return jsonify({
            "status": "error",
            "message": "Your device is blocked"
        })

    user_agent = request.headers.get("User-Agent", "")
    hwid = f"{ip}|{user_agent}"

    if license_key not in LICENSE_KEYS:
        return jsonify({"status": "error", "message": "License not found"})

    lic = LICENSE_KEYS[license_key]

    if lic["hwid"] == "":
        lic["hwid"] = hwid

    elif lic["hwid"] != hwid:
        return jsonify({
            "status": "error",
            "message": "License already used on another device"
        })

    session["logged_in"] = True
    send_login_info()

    return jsonify({"status": "success"})
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

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if ip:
        ip = ip.split(",")[0].strip()

    # Page open pe block message nahi dikhayega
    if request.method == "POST":

        # Login submit pe IP block check
        if ip in BLOCKED_IPS:
            return render_template("login.html", error="Your Device is blocked")

        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            
            session["logged_in"] = True
            send_login_info()   # webhook only on success
            
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")




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

# -------------------- USER MANAGEMENT --------------------

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


@app.route("/get_users", methods=["POST"])
def get_users():

    data = load_data()
    category = request.form["category"]

    users = data.get(category, [])

    for u in users:

        if is_online(u.get("LastSeen")):
            u["Online"] = "Online"
        else:
            u["Online"] = "Offline"

    return jsonify(users)


@app.route("/client_login", methods=["POST"])
def client_login():
    data = load_data()

    category = request.form["category"]
    username = request.form["username"]
    password = request.form["password"]
    hwid = request.form["hwid"]

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip:
        ip = ip.split(",")[0].strip()

    pc_name = request.form.get("pcname", "Unknown")

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

                send_client_login(category, username, password, ip, hwid, pc_name)

                return jsonify({
                    "status": "success",
                    "message": "HWID bound. Login success",
                    "expiry": user["Expiry"]
                })

            if user["HWID"] != hwid:
                return jsonify({"status": "error", "message": "HWID mismatch"})

            send_client_login(category, username, password, ip, hwid, pc_name)

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
