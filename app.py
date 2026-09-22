import os
import secrets
from datetime import datetime

import requests
from flask import Flask, jsonify, request, send_file


app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# Временное хранилище.
# Данные пропадут после перезапуска Railway.
requests_storage = {}


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=10,
        )

        return response.ok

    except requests.RequestException:
        return False


def generate_request_id():
    return secrets.token_hex(4).upper()


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}

    coupon = str(data.get("coupon", "")).strip()
    server = str(data.get("server", "")).strip()

    if not coupon or not server:
        return jsonify({
            "success": False,
            "error": "Заполните оба поля."
        }), 400

    if len(coupon) > 200 or len(server) > 200:
        return jsonify({
            "success": False,
            "error": "Слишком длинное значение."
        }), 400

    request_id = generate_request_id()

    created_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    requests_storage[request_id] = {
        "coupon": coupon,
        "server": server,
        "nickname": None,
        "created_at": created_at,
        "confirmed": False,
    }

    telegram_message = (
        "🆕 <b>НОВАЯ ЗАЯВКА</b>\n\n"
        f"🆔 ID: <code>{request_id}</code>\n"
        f"🎟 Купон: <code>{coupon}</code>\n"
        f"🖥 Сервер: <code>{server}</code>\n"
        f"🕐 Время: {created_at}\n\n"
        "⏳ Статус: ожидается ник"
    )

    if not send_telegram(telegram_message):
        requests_storage.pop(request_id, None)

        return jsonify({
            "success": False,
            "error": "Не удалось отправить заявку."
        }), 500

    return jsonify({
        "success": True,
        "request_id": request_id
    })


@app.route("/confirm", methods=["POST"])
def confirm():
    data = request.get_json(silent=True) or {}

    request_id = str(data.get("request_id", "")).strip()
    nickname = str(data.get("nickname", "")).strip()

    if not request_id or not nickname:
        return jsonify({
            "success": False,
            "error": "Введите ник."
        }), 400

    if len(nickname) > 100:
        return jsonify({
            "success": False,
            "error": "Слишком длинный ник."
        }), 400

    application = requests_storage.get(request_id)

    if not application:
        return jsonify({
            "success": False,
            "error": "Заявка не найдена."
        }), 404

    if application["confirmed"]:
        return jsonify({
            "success": False,
            "error": "Заявка уже подтверждена."
        }), 400

    application["nickname"] = nickname
    application["confirmed"] = True

    confirmed_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    telegram_message = (
        "✅ <b>ЗАЯВКА ПОДТВЕРЖДЕНА</b>\n\n"
        f"🆔 ID: <code>{request_id}</code>\n"
        f"🎟 Купон: <code>{application['coupon']}</code>\n"
        f"🖥 Сервер: <code>{application['server']}</code>\n"
        f"👤 Ник: <code>{nickname}</code>\n"
        f"🕐 Время: {confirmed_at}\n\n"
        "🟢 Статус: подтверждено"
    )

    if not send_telegram(telegram_message):
        return jsonify({
            "success": False,
            "error": "Не удалось отправить подтверждение."
        }), 500

    return jsonify({
        "success": True
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
