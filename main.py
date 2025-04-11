import time
import requests

# Credenciais do seu bot Telegram
TELEGRAM_TOKEN = "7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM"
CHAT_ID = "6197066344"

def send_telegram_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    response = requests.post(url, data=payload)
    print(f"Telegram response: {response.status_code}, {response.text}", flush=True)

if __name__ == "__main__":
    print("Bot Telegram ativo!", flush=True)
    while True:
        print("Enviando alerta Telegram...", flush=True)
        send_telegram_alert("Bitcoin está próximo do ATH!")
        time.sleep(600)  # Espera 10 minutos entre os alertas
