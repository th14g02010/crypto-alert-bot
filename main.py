import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM')
CHAT_ID = os.getenv('CHAT_ID', '6197066344')
SYMBOL = os.getenv('SYMBOL', 'SOLUSDT')
INTERVAL = os.getenv('INTERVAL', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

# Inicialização do Flask
app = Flask(__name__)

# ================== FUNÇÕES DE API ==================
def get_binance_candles(symbol, interval, limit=21):
    """Obtém candles da Binance com fallback para múltiplos endpoints"""
    BINANCE_URLS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json'
    }
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    for base_url in BINANCE_URLS:
        try:
            response = requests.get(
                f"{base_url}/api/v3/klines",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if not response.text.strip().startswith(('<!DOCTYPE', '<html')):
                data = response.json()
                return [{
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "time": datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M'),
                    "source": "Binance"
                } for c in data]
                
        except Exception:
            continue
    
    return None

def get_bybit_candles(symbol, interval, limit=21):
    """Fallback para API da Bybit"""
    try:
        interval_map = {
            '1h': '60',
            '4h': '240',
            '1d': 'D'
        }
        
        response = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol,
                "interval": interval_map.get(interval, '60'),
                "limit": limit
            },
            timeout=10
        )
        
        data = response.json()
        return [{
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "time": datetime.fromtimestamp(int(c["startTime"])/1000).strftime('%Y-%m-%d %H:%M'),
            "source": "Bybit"
        } for c in data["result"]["list"]]
        
    except Exception as e:
        print(f"Erro na Bybit API: {e}")
        return None

def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Tenta Binance primeiro, depois Bybit"""
    candles = get_binance_candles(symbol, interval, limit)
    if not candles:
        print("🔁 Binance falhou, tentando Bybit...")
        candles = get_bybit_candles(symbol, interval, limit)
    return candles

# ================== LÓGICA DO BOT ==================
def send_telegram_alert(message):
    """Envia alertas para o Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"Erro no Telegram: {e}")

def analyze_market():
    """Analisa o mercado e envia alertas"""
    candles = get_candles()
    if not candles:
        return False

    last_candle = candles[-1]
    message = (
        f"📊 **Dados do Mercado** ({SYMBOL})\n\n"
        f"🕒 Hora: {last_candle['time']}\n"
        f"💰 Preço: ${last_candle['close']:.4f}\n"
        f"📈 Alta: ${last_candle['high']:.4f}\n"
        f"📉 Baixa: ${last_candle['low']:.4f}\n"
        f"🔍 Fonte: {last_candle['source']}"
    )
    send_telegram_alert(message)
    return True

# ================== ROTAS FLASK ==================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "symbol": SYMBOL,
        "data_source": "Binance/Bybit",
        "interval": INTERVAL
    })

# ================== LOOP PRINCIPAL ==================
def trading_loop():
    while True:
        try:
            analyze_market()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Verifica configurações
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Configure TELEGRAM_TOKEN e CHAT_ID no Render!")
    else:
        # Inicia o bot em thread separada
        Thread(target=trading_loop, daemon=True).start()
        
        # Inicia o servidor Flask (obrigatório no Render)
        app.run(host='0.0.0.0', port=8000)
