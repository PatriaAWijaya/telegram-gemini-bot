import os
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = genai.Client(api_key=GEMINI_API_KEY)

# Dummy Server untuk Health Check Render Web Service
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Telegram Aktif!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Dummy HTTP server berjalan di port {port}")
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "Halo! Aku bot Gemini AI milikmu. Silakan kirimkan pertanyaan apa saja!"
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action("typing")
    
    # Memberikan instruksi konteks tanggal & waktu real-time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys_instruction = f"Hari ini adalah tanggal dan waktu: {now}."
    
    config = types.GenerateContentConfig(
        system_instruction=sys_instruction
    )
    
    try:
        # Coba jalankan dengan model utama gemini-3.8-flash
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=user_text,
                config=config
            )
        except Exception as e:
            # Fallback jika model utama 503 / sibuk
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                logging.warning("Gemini 3.8 Flash sedang sibuk, beralih ke Gemini 2.5 Flash...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_text,
                    config=config
                )
            else:
                raise e

        reply_text = response.text
        
        # Penanganan batas panjang pesan Telegram
        if len(reply_text) > 4000:
            for i in range(0, len(reply_text), 4000):
                await update.message.reply_text(reply_text[i:i+4000])
        else:
            await update.message.reply_text(reply_text)
            
    except Exception as e:
        logging.error(f"Error detail: {e}")
        await update.message.reply_text("Server Gemini sedang sibuk, silakan coba kirim ulang pesan beberapa saat lagi.")

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot Telegram Gemini berhasil dijalankan!")
    app.run_polling()