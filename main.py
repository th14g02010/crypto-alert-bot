import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTC-USDT')  # Formato KuCoin: BTC-USDT
INTERVAL = os.getenv('INTERVAL', '1hour')  # KuCoin usa '1hour' em vez de '1h'
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== FUNÇÕES DA KUCOIN API ==================
def get_kucoin_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """
    Obtém candles da KuCoin API
    Intervalos suportados: 
    1min, 3min, 5min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week
    """
    try:
        url = "https://api.kucoin.com/api/v1/market/candles"
        params = {
            "symbol": symbol,
            "type": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == "200000" and data.get("data"):
            candles = []
            for candle in data["data"]:
                candles.append({
                    "time": datetime.fromtimestamp(int(candle[0])).strftime('%Y-%m-%d %H:%M'),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "source": "KuCoin"
                })
            return candles[::-1]  # Inverte para ordem cronológica correta
        else:
            print(f"KuCoin API Error: {data.get('msg', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Erro na KuCoin API: {str(e)[:100]}")
        return None

# ================== LÓGICA DO BOT ==================
def send_telegram_alert(message):
    """Envia alertas para o Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Configurações do Telegram ausentes")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Erro no Telegram: {str(e)[:50]}")
        return False

def analyze_market():
    """Executa análise de mercado"""
    print("\n🔍 Analisando mercado via KuCoin...")
    candles = get_kucoin_c
