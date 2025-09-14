import os
import io
import shutil
import traceback
from gtts import gTTS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from colorama import init, Fore
from pydub import AudioSegment

init(autoreset=True)

# ---------------- Utility ----------------
def read_file(path):
    if not os.path.exists(path):
        print(Fore.RED + f"[ERROR] File not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

# ---------------- Config ----------------
BOT_TOKEN = read_file("token.txt")
if not BOT_TOKEN:
    raise SystemExit("❌ token.txt missing or empty!")

bot = telebot.TeleBot(BOT_TOKEN)

# user data
user_prefs = {}
last_text = {}

DEFAULT_PREFS = {"lang": "hi", "speed": "normal", "out": "voice"}

# ---------------- Banner ----------------
def show_banner():
    os.system("clear")
    print(Fore.GREEN + "===============================")
    print(Fore.GREEN + "      AMARJIT TTS BOT")
    print(Fore.GREEN + "===============================")
    print(Fore.YELLOW + "Created by Amarjit\n")

# ---------------- ffmpeg Check ----------------
FFMPEG_EXISTS = shutil.which("ffmpeg") is not None
if not FFMPEG_EXISTS:
    print(Fore.RED + "⚠️  ffmpeg not found! Install it with: pkg install ffmpeg")

# ---------------- Generate Voice ----------------
def generate_tts(text, lang="hi", speed="normal"):
    slow = True if speed == "slow" else False
    tts = gTTS(text=text, lang=lang, slow=slow)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp

def convert_to_ogg(mp3_fp):
    if not FFMPEG_EXISTS:
        return None
    mp3_fp.seek(0)
    audio = AudioSegment.from_file(mp3_fp, format="mp3")
    ogg_fp = io.BytesIO()
    audio.export(ogg_fp, format="ogg", codec="libopus")
    ogg_fp.seek(0)
    return ogg_fp

# ---------------- Keyboard ----------------
def options_keyboard(user_id):
    prefs = user_prefs.get(user_id, DEFAULT_PREFS.copy())
    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton(("✅ " if prefs['lang']=="hi" else "") + "Hindi", callback_data="lang|hi"),
        InlineKeyboardButton(("✅ " if prefs['lang']=="en" else "") + "English", callback_data="lang|en")
    )
    kb.add(
        InlineKeyboardButton(("✅ " if prefs['speed']=="normal" else "") + "Normal", callback_data="speed|normal"),
        InlineKeyboardButton(("✅ " if prefs['speed']=="slow" else "") + "Slow", callback_data="speed|slow"),
        InlineKeyboardButton(("✅ " if prefs['speed']=="fast" else "") + "Fast", callback_data="speed|fast")
    )
    kb.add(
        InlineKeyboardButton(("✅ " if prefs['out']=="voice" else "") + "Voice", callback_data="out|voice"),
        InlineKeyboardButton(("✅ " if prefs['out']=="audio" else "") + "Audio", callback_data="out|audio")
    )
    kb.add(InlineKeyboardButton("🔊 Generate", callback_data="generate"))
    return kb

# ---------------- Bot Commands ----------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    user_prefs[user_id] = DEFAULT_PREFS.copy()
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Amarjit TTS Bot!\n\n"
        "Send me any text, and I will convert it into speech.\n"
        "Choose language, speed, and output type using the buttons below.",
        reply_markup=options_keyboard(user_id)
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    txt = message.text.strip()
    last_text[user_id] = txt
    if user_id not in user_prefs:
        user_prefs[user_id] = DEFAULT_PREFS.copy()
    bot.send_message(message.chat.id, "📝 Text saved. Now click *Generate* to convert.",
                     reply_markup=options_keyboard(user_id))

# ---------------- Callback Handler ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if user_id not in user_prefs:
        user_prefs[user_id] = DEFAULT_PREFS.copy()

    data = call.data.split("|")

    if data[0] in ["lang", "speed", "out"]:
        user_prefs[user_id][data[0]] = data[1]
        bot.answer_callback_query(call.id, f"{data[0].capitalize()} set to {data[1]}")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=options_keyboard(user_id))
        return

    if data[0] == "generate":
        text = last_text.get(user_id)
        if not text:
            bot.answer_callback_query(call.id, "❌ No text found. Send text first.")
            return

        prefs = user_prefs[user_id]
        bot.answer_callback_query(call.id, "Generating audio...")

        try:
            mp3_fp = generate_tts(text, prefs['lang'], prefs['speed'])

            if prefs['out'] == "voice" and FFMPEG_EXISTS:
                ogg_fp = convert_to_ogg(mp3_fp)
                if ogg_fp:
                    bot.send_voice(call.message.chat.id, ogg_fp, caption="🔊 Voice Generated")
                    return

            # fallback to mp3
            mp3_fp.name = "speech.mp3"
            bot.send_audio(call.message.chat.id, mp3_fp, caption="🔊 Audio Generated")

        except Exception as e:
            traceback.print_exc()
            bot.send_message(call.message.chat.id, f"❌ Error generating audio: {e}")

# ---------------- Run Bot ----------------
def main():
    show_banner()
    print(Fore.CYAN + "Bot is running. Press Ctrl+C to stop.\n")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    main()
