import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import mysql.connector.pooling
import google.generativeai as genai
import markdown
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing from .env")

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

dbconfig = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "trekking"),
    "autocommit": True,
    "ssl_disabled": True,
}

pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **dbconfig
)

def get_conn():
    return pool.get_connection()

def fetch_one(query, params=()):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def fetch_all(query, params=()):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def execute_query(query, params=()):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

def create_users_table():
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(200) NOT NULL,
                number VARCHAR(20) NOT NULL,
                last_lat FLOAT NULL,
                last_lon FLOAT NULL
            )
        """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

create_users_table()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")
genai.configure(api_key=GEMINI_API_KEY)

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY")
FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"

def send_sms(phone_number, message):
    if not FAST2SMS_API_KEY:
        return False, "FAST2SMS_API_KEY is missing from .env"

    payload = {
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": phone_number,
    }
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }

    try:
        response = requests.post(
            FAST2SMS_URL,
            data=payload,
            headers=headers,
            timeout=15,
        )
        if response.status_code == 200:
            return True, response.text
        return False, response.text
    except requests.RequestException as exc:
        return False, str(exc)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/auth/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Please enter username and password."
            return render_template("login.html", error=error)

        user = fetch_one(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)

@app.route("/auth/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirmPassword", "")
        number = request.form.get("number", "").strip()

        if not username or not email or not password or not confirm or not number:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match"
        elif fetch_one("SELECT * FROM users WHERE email=%s", (email,)):
            error = "User already exists"
        else:
            password_hash = generate_password_hash(password)
            try:
                execute_query(
                    """
                    INSERT INTO users
                    (username, email, password_hash, number)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (username, email, password_hash, number)
                )
                return redirect(url_for("login"))
            except Exception as exc:
                print("Signup error:", exc)
                error = "Unable to create account. Please try again."

    return render_template("signup.html", error=error)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/dashboard/btn-page")
def button_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    trek_mode = request.args.get("mode", "").strip().capitalize()

    trek_images = {
        "Easy": "EASY.jpg",
        "Moderate": "MODERATE.jpg",
        "Hard": "HARD.jpg",
    }

    if trek_mode not in trek_images:
        trek_mode = "Not Selected"
        trek_image = "DEFAULT.jpg"
    else:
        trek_image = trek_images[trek_mode]

    return render_template(
        "button.html",
        trek_mode=trek_mode,
        trek_image=trek_image,
        emergency_phone=os.getenv("EMERGENCY_PHONE", "")
    )


@app.route("/dashboard/action/SOS")
def sos_action():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    user = fetch_one(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    message = (
        "🚨 HELP I AM IN TROUBLE 🚨\n"
        "🏃🏻‍♂️ Message from Trekking Club 🏃🏻‍♂️"
    )
    success, result = send_sms(user["number"], message)

    if success:
        return jsonify({
            "status": "success",
            "message": "SOS sent successfully"
        })

    return jsonify({"status": "fail", "error": result}), 502

@app.route("/dashboard/action/TRACK", methods=["POST"])
def track_action():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON body received"
        }), 400

    lat = data.get("lat")
    lon = data.get("lon")

    if lat is None or lon is None:
        return jsonify({
            "status": "error",
            "message": "Missing lat or lon"
        }), 400

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Invalid lat/lon"
        }), 400

    if not -90 <= lat_f <= 90:
        return jsonify({
            "status": "error",
            "message": "Latitude must be between -90 and 90"
        }), 400

    if not -180 <= lon_f <= 180:
        return jsonify({
            "status": "error",
            "message": "Longitude must be between -180 and 180"
        }), 400

    user = fetch_one(
        "SELECT * FROM users WHERE id=%s",
        (session["user_id"],)
    )
    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    try:
        execute_query(
            """
            UPDATE users
            SET last_lat=%s, last_lon=%s
            WHERE id=%s
            """,
            (lat_f, lon_f, user["id"])
        )
    except Exception as exc:
        print("DB update error:", exc)
        return jsonify({
            "status": "error",
            "message": "Unable to update location"
        }), 500

    live_page_link = url_for(
        "public_track",
        user_id=user["id"],
        _external=True
    )
    google_maps_link = f"https://www.google.com/maps?q={lat_f},{lon_f}"

    if request.args.get("send_sms", "").lower() == "true":
        message = (
            "📍 My Location Update:\n"
            f"Google Maps: {google_maps_link}\n"
            f"Live Tracking: {live_page_link}"
        )
        success, result = send_sms(user["number"], message)

        if success:
            return jsonify({
                "status": "success",
                "google_maps_link": google_maps_link,
                "live_page_link": live_page_link
            })

        return jsonify({
            "status": "fail",
            "error": result,
            "google_maps_link": google_maps_link,
            "live_page_link": live_page_link
        }), 502

    return jsonify({
        "status": "success",
        "google_maps_link": google_maps_link,
        "live_page_link": live_page_link
    })

@app.route("/track-data/<int:user_id>")
def track_data(user_id):
    user = fetch_one(
        "SELECT last_lat, last_lon FROM users WHERE id=%s",
        (user_id,)
    )
    if not user or user["last_lat"] is None or user["last_lon"] is None:
        return jsonify({
            "status": "error",
            "message": "Location not available"
        }), 404

    return jsonify({
        "status": "success",
        "lat": float(user["last_lat"]),
        "lon": float(user["last_lon"])
    })

@app.route("/track/<int:user_id>")
def public_track(user_id):
    return render_template(
        "track.html",
        user_id=user_id,
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", "")
    )

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        if request.method == "POST":
            return jsonify({
                "reply": "Please log in to use the chatbot."
            }), 401
        return redirect(url_for("login"))

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        msg = str(data.get("message", "")).strip()

        if not msg:
            return jsonify({"reply": "Please enter a message."}), 400

        if len(msg) > 4000:
            return jsonify({
                "reply": "Message is too long. Please keep it under 4000 characters."
            }), 400

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(msg)
            reply_text = getattr(response, "text", None)

            if not reply_text:
                reply_text = "I could not generate a response."

            return jsonify({
                "reply": markdown.markdown(reply_text)
            })
        except Exception as exc:
            print("Gemini error:", exc)
            return jsonify({
                "reply": "<p style='color:red'>AI service is temporarily unavailable.</p>"
            }), 502

    return render_template("chat.html")

@app.route("/list-models")
def list_models():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        models = genai.list_models()
        return jsonify({
            "available_models": [model.name for model in models]
        })
    except Exception as exc:
        print("List models error:", exc)
        return jsonify({
            "error": "Unable to retrieve models"
        }), 502

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in {
        "1", "true", "yes", "on"
    }
    port = int(os.getenv("PORT", "3000"))

    app.run(
        debug=debug_mode,
        host="127.0.0.1",
        port=port
    )
