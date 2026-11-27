# -*- coding: utf-8 -*-
"""Bot va veb-ilovani birga ishga tushiradi:  python run.py"""
import threading

import config
from server import app
from bot import run_bot


def _serve():
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=config.PORT, threads=8)
    except ImportError:
        app.run(host="0.0.0.0", port=config.PORT, threaded=True)


if __name__ == "__main__":
    if config.BOT_TOKEN:
        threading.Thread(target=_serve, daemon=True).start()
        run_bot()          # asosiy oqimda
    else:
        print("BOT_TOKEN berilmagan — faqat veb-server ishga tushdi.")
        _serve()
