import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações via variáveis de ambiente (NUNCA coloque dados sensíveis no código!)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Obrigatório no Render
CHAT_ID = os.getenv('CHAT_ID')               # Obrigatório no Render
SYMBOL = os.getenv('SYMBOL', 'SOLUSDT')      # Par padrão
INTERVAL = os.getenv('INTERVAL', '1h')       # Tempo gráfico padrão
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

# Inicialização do Flask
app = Flask(__name__)

# Variável de estado
last_signal = None

def send_telegram_alert(message):
    """Envia mensagem para o Telegram com tratamento de erros"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Token ou Chat ID do Telegram não configurados!")
        return None

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Erro ao enviar alerta: {e}")
        return None

# ... (mantenha todas as outras funções IGUAIS ao código anterior: get_candles, get_trend, detect_engulfing, format_price)

def trading_bot():
    """Loop principal do bot"""
    global last_signal

    print(f"\n🔍 Iniciando monitoramento de {SYMBOL} ({INTERVAL})")
    print(f"⏳ Intervalo de verificação: {CHECK_INTERVAL//60} minutos")

    while True:
        try:
            candles = get_candles()
            if not candles:
                time.sleep(60)
                continue

            current = candles[-1]
            previous = candles[-2]
            trend = get_trend(candles)
            trend_icon = "🔺" if trend == "up" else "🔻" if trend == "down" else "➖"

            # Lógica de negociação (igual ao anterior)
            if detect_engulfing(previous, current, "bullish") and last_signal != "bullish":
                message = f"🚨 **ALERTA DE COMPRA** ({SYMBOL})..."
                send_telegram_alert(message)
                last_signal = "bullish"

            elif detect_engulfing(previous, current, "bearish") and last_signal != "bearish":
                message = f"⚠️ **ALERTA DE VENDA** ({SYMBOL})..."
                send_telegram_alert(message)
                last_signal = "bearish"

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Erro no bot: {e}")
            time.sleep(60)

@app.route('/')
def health_check():
    """Rota para verificação de status"""
    return jsonify({
        "status": "active",
        "symbol": SYMBOL,
        "last_check": datetime.now().isoformat(),
        "environment": "production" if os.getenv('RENDER') else "development"
    })

if __name__ == "__main__":
    # Verifica credenciais antes de iniciar
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ ERRO: Variáveis TELEGRAM_TOKEN e CHAT_ID não configuradas!")
        print("Configure-as no painel do Render -> Environment")
    else:
        Thread(target=trading_bot, daemon=True).start()
    
    app.run(host='0.0.0.0', port=8000)
