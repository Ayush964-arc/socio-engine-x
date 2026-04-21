from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
import os
from dotenv import load_dotenv
from utils.youtube import get_channel_stats
from utils.ai_analysis import analyze_channel
import plotly.graph_objects as go
import plotly.utils
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ─────────────────────────────────────────
# PASSWORD — change this to whatever you want
# ─────────────────────────────────────────
APP_PASSWORD = "socioengine2024"


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.route("/")
def root():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data     = request.get_json()
        password = data.get("password", "")
        if password == APP_PASSWORD:
            session["logged_in"] = True
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Wrong password. Try again."})
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


# ─────────────────────────────────────────
# API — FETCH CHANNEL
# ─────────────────────────────────────────
@app.route("/api/channel", methods=["POST"])
def fetch_channel():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data          = request.get_json()
    channel_input = data.get("channel", "").strip()

    if not channel_input:
        return jsonify({"error": "No channel provided"}), 400

    channel_data = get_channel_stats(channel_input)

    if not channel_data:
        return jsonify({"error": "Channel not found"}), 404

    return jsonify({"success": True, "data": channel_data})


# ─────────────────────────────────────────
# API — AI ANALYSIS
# ─────────────────────────────────────────
@app.route("/api/ai", methods=["POST"])
def ai_analysis():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data         = request.get_json()
    channel_data = data.get("channel_data", {})

    if not channel_data:
        return jsonify({"error": "No channel data"}), 400

    tips = analyze_channel(channel_data)
    return jsonify({"success": True, "tips": tips})


# ─────────────────────────────────────────
# API — CHANNEL BATTLE
# ─────────────────────────────────────────
@app.route("/api/battle", methods=["POST"])
def battle():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    ch1 = data.get("channel1", "").strip()
    ch2 = data.get("channel2", "").strip()

    if not ch1 or not ch2:
        return jsonify({"error": "Both channels required"}), 400

    try:
        d1 = get_channel_stats(ch1)
        d2 = get_channel_stats(ch2)
    except Exception as e:
        return jsonify({"error": f"Fetch failed: {str(e)}"}), 500

    if not d1:
        return jsonify({"error": f"Channel not found: {ch1}"}), 404
    if not d2:
        return jsonify({"error": f"Channel not found: {ch2}"}), 404

    results = {
        "channel1": d1,
        "channel2": d2,
        "winners": {
            "subscribers":     1 if d1["subscribers"]     >= d2["subscribers"]     else 2,
            "total_views":     1 if d1["total_views"]      >= d2["total_views"]      else 2,
            "engagement_rate": 1 if d1["engagement_rate"]  >= d2["engagement_rate"]  else 2,
            "avg_views":       1 if d1["avg_views"]         >= d2["avg_views"]         else 2,
            "video_count":     1 if d1["video_count"]       >= d2["video_count"]       else 2,
        }
    }
    w1 = sum(1 for v in results["winners"].values() if v == 1)
    w2 = sum(1 for v in results["winners"].values() if v == 2)
    results["overall_winner"] = 1 if w1 >= w2 else 2
    return jsonify({"success": True, "data": results})


# ─────────────────────────────────────────
# API — GROWTH PREDICTION
# ─────────────────────────────────────────
@app.route("/api/predict", methods=["POST"])
def predict():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data         = request.get_json()
    channel_data = data.get("channel_data", {})

    subs  = channel_data.get("subscribers", 0)
    views = channel_data.get("total_views",  0)
    vids  = channel_data.get("video_count",  1)

    avg_subs_per_video = subs / max(vids, 1)
    posting_rate       = 2

    prediction = {
        "months":  [1, 3, 6, 12],
        "current": subs,
        "predicted_subs": [
            int(subs + avg_subs_per_video * posting_rate * m)
            for m in [1, 3, 6, 12]
        ],
        "predicted_views": [
            int(views + (views / max(vids, 1)) * posting_rate * m)
            for m in [1, 3, 6, 12]
        ]
    }

    return jsonify({"success": True, "data": prediction})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)