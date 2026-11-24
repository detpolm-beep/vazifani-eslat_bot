# Lokal ishlatish uchun config.py fayl yarating:
# BOT_TOKEN = "tokeningiz"
#
# Railway uchun Variables bo'limiga qo'shing:
# BOT_TOKEN = tokeningiz

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_TOKENINGIZNI_KIRITING")
