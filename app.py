from flask import Flask, request, jsonify, send_file
import requests
import secrets
from datetime import datetime

app = Flask(__name__)

# =========================
# НАСТРОЙКИ TELEGRAM
# =========================

BOT_TOKEN = "8671990790:AAFJ9HAc4SWswxBNKYgIJdqiO6xlI1YRqzw"
CHAT_ID = "-1003571283881"

# Временное хранилище в памяти.
# После перезапуска app.py заявки исчезнут.
requests_storage = {}


def send_telegram(message):
    """Отправляет сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )

        return response.ok

    except requests.RequestException:
        return False


def generate_request_id():
    """Генерирует короткий ID заявки."""
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

    # Ограничиваем размер входных данных
    if len(coupon) > 200 or len(server) > 200:
        return jsonify({
            "success": False,
            "error": "Слишком длинное значение."
        }), 400

    request_id = generate_request_id()

    requests_storage[request_id] = {
        "coupon": coupon,
        "server": server,
        "nickname": None,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "confirmed": False
    }

    telegram_message = (
        "🆕 <b>НОВАЯ ЗАЯВКА</b>\n\n"
        f"🆔 ID: <code>{request_id}</code>\n"
        f"🎟 Купон: <code>{coupon}</code>\n"
        f"🖥 Сервер: <code>{server}</code>\n"
        f"🕐 Время: {requests_storage[request_id]['created_at']}\n\n"
        "⏳ Статус: ожидается подтверждение ника"
    )

    telegram_ok = send_telegram(telegram_message)

    if not telegram_ok:
        # Удаляем заявку, если Telegram недоступен
        requests_storage.pop(request_id, None)

        return jsonify({
            "success": False,
            "error": "Не удалось отправить заявку. Попробуйте ещё раз."
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
            "error": "Заявка не найдена или срок её действия истёк."
        }), 404

    if application["confirmed"]:
        return jsonify({
            "success": False,
            "error": "Эта заявка уже подтверждена."
        }), 400

    application["nickname"] = nickname
    application["confirmed"] = True

    telegram_message = (
        "✅ <b>ЗАЯВКА ПОДТВЕРЖДЕНА</b>\n\n"
        f"🆔 ID: <code>{request_id}</code>\n"
        f"🎟 Купон: <code>{application['coupon']}</code>\n"
        f"🖥 Сервер: <code>{application['server']}</code>\n"
        f"👤 Ник: <code>{nickname}</code>\n"
        f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        "🟢 Статус: подтверждено"
    )

    telegram_ok = send_telegram(telegram_message)

    if not telegram_ok:
        return jsonify({
            "success": False,
            "error": "Не удалось отправить подтверждение."
        }), 500

    return jsonify({
        "success": True
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
