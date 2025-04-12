import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'SOLUSDT')
INTERVAL = os.getenv('INTERVAL', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== FUNÇÕES DE API ==================
def get_binance_candles(symbol, interval, limit=21):
    """Obtém candles da Binance com tratamento de erros"""
    BINANCE_URLS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com"
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
                timeout=15
            )
            
            if response.status_code == 200 and not response.text.startswith(('<!DOCTYPE', '<html')):
                data = response.json()
                return [{
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "time": datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M'),
                    "source": "Binance"
                } for c in data]
                
        except Exception as e:
            print(f"Erro na Binance ({base_url}): {str(e)[:100]}")
            continue
    
    return None

def get_kucoin_candles(symbol, interval, limit=21):
    """Fallback para API da KuCoin quando Binance falha"""
    try:
        interval_map = {
            '1m': '1min', '5m': '5min', '15m': '15min',
            '30m': '30min', '1h': '1hour', '4h': '4hour',
            '6h': '6hour', '12h': '12hour', '1d': '1day'
        }
        
        response = requests.get(
            "https://api.kucoin.com/api/v1/market/candles",
            params={
                "symbol": symbol.replace('/', '-'),
                "type": interval_map.get(interval, '1hour'),
                "limit": limit
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                return [{
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "time": datetime.fromtimestamp(int(c[0])).strftime('%Y-%m-%d %H:%M'),
                    "source": "KuCoin"
                } for c in data["data"]]
                
    except Exception as e:
        print(f"Erro na KuCoin API: {str(e)[:100]}")
    
    return None

def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém dados com fallback para KuCoin"""
    candles = get_binance_candles(symbol, interval, limit)
    if not candles:
        print("🔁 Binance falhou, tentando KuCoin...")
        candles = get_kucoin_candles(symbol, interval, limit)
    return candles or []

# ================== LÓGICA DO BOT ==================
def send_telegram_alert(message):
    """Envia alertas para o Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Token ou Chat ID do Telegram não configurados!")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"Erro no Telegram: {str(e)[:100]}")

def analyze_market():
    """Analisa o mercado e envia alertas"""
    candles = get_candles()
    if not candles:
        print("❌ Não foi possível obter dados do mercado")
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

def trading_loop():
    """Loop principal de trading"""
    print("\n🤖 Bot iniciado. Pressione Ctrl+C para sair.")
    while True:
        try:
            analyze_market()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Erro no loop principal: {str(e)[:100]}")
            time.sleep(60)

# ================== ROTAS FLASK ==================
@app.route('/')
def health_check():
    return jsonify({
        "status": "online",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "last_check": datetime.now().isoformat()
    })

# ================== INICIALIZAÇÃO ==================
if __name__ == "__main__":
    # Teste rápido das APIs
    print("=== TESTE DE CONEXÃO ===")
    print("Binance:", "OK" if get_binance_candles(SYMBOL, INTERVAL, 1) else "Falhou")
    print("KuCoin:", "OK" if get_kucoin_candles(SYMBOL, INTERVAL, 1) else "Falhou")
    
    # Inicia o bot em thread separada
    Thread(target=trading_loop, daemon=True).start()
    
    # Inicia o servidor Flask (obrigatório no Render)
    app.run(host='0.0.0.0', port=8000)
