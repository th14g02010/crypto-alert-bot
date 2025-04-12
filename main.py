import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# ========== CONFIGURAÇÕES ==========
# Defina as variáveis primeiro
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM')
CHAT_ID = os.getenv('CHAT_ID', '6197066344')
SYMBOL = os.getenv('SYMBOL', 'SOLUSDT')  # Definindo SYMBOL aqui
INTERVAL = os.getenv('INTERVAL', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

# ========== FUNÇÕES ==========
def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém candles da Binance API"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        candles = []
        for candle in response.json():
            if len(candle) >= 5:
                candles.append({
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "time": datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d %H:%M')
                })
        return candles
    except Exception as e:
        print(f"Erro ao obter candles: {e}")
        return []

# ... (outras funções como get_trend, detect_engulfing, etc.)

def trading_bot():
    """Função principal do bot"""
    global last_signal
    last_signal = None
    
    print(f"\n🔍 Iniciando monitoramento de {SYMBOL} ({INTERVAL})")
    print(f"⏳ Intervalo de verificação: {CHECK_INTERVAL//60} minutos")
    
    while True:
        try:
            candles = get_candles()  # Agora SYMBOL está definido
            if not candles:
                time.sleep(60)
                continue
                
            # ... (restante da lógica do bot)
            
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Erro no bot: {e}")
            time.sleep(60)

# ========== FLASK ==========
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "symbol": SYMBOL,
        "interval": INTERVAL
    })

if __name__ == "__main__":
    # Verifica se as variáveis essenciais estão definidas
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Erro: TELEGRAM_TOKEN e CHAT_ID devem ser definidos!")
    else:
        Thread(target=trading_bot, daemon=True).start()
        app.run(host='0.0.0.0', port=8000)
