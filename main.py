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

# ================== FUNÇÕES DE API MELHORADAS ==================
def get_binance_candles(symbol, interval, limit=21):
    """Obtém candles da Binance com tratamento de erros completo"""
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
            
            # Verifica se a resposta é JSON válido
            if response.text.strip() and not response.text.startswith(('<!DOCTYPE', '<html')):
                data = response.json()
                if isinstance(data, list):
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

def get_bybit_candles(symbol, interval, limit=21):
    """API da Bybit com tratamento de erros reforçado"""
    try:
        # Mapeamento de intervalos
        interval_map = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15',
            '30m': '30', '1h': '60', '2h': '120', '4h': '240',
            '6h': '360', '12h': '720', '1d': 'D', '1w': 'W'
        }
        
        # Verifica se o símbolo precisa de ajuste (ex: SOLUSDT → SOLUSDT)
        bybit_symbol = symbol.replace('/', '') if '/' in symbol else symbol
        
        response = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "spot",
                "symbol": bybit_symbol,
                "interval": interval_map.get(interval, '60'),
                "limit": str(limit)
            },
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=15
        )
        
        # Debug: Verifique a resposta bruta
        print(f"Bybit Response: {response.status_code} - {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result") and data["result"].get("list"):
                return [{
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                    "time": datetime.fromtimestamp(int(c["startTime"])/1000).strftime('%Y-%m-%d %H:%M'),
                    "source": "Bybit"
                } for c in data["result"]["list"]]
            else:
                print("Bybit: Estrutura de dados inválida")
        else:
            print(f"Bybit API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Erro crítico na Bybit API: {str(e)}")
    
    return None

def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém dados com fallback inteligente"""
    print(f"\n🔄 Obtendo candles ({symbol} {interval})...")
    
    # Tenta Binance primeiro
    candles = get_binance_candles(symbol, interval, limit)
    
    # Fallback para Bybit se necessário
    if not candles:
        print("🔁 Binance falhou, tentando Bybit...")
        candles = get_bybit_candles(symbol, interval, limit)
    
    return candles or []

# ... (mantenha o resto do código igual: send_telegram_alert, analyze_market, etc.)

if __name__ == "__main__":
    # Teste rápido das APIs
    print("=== TESTE DE API ===")
    print("Binance:", len(get_binance_candles(SYMBOL, INTERVAL, 1)) if get_binance_candles(SYMBOL, INTERVAL, 1) else "Binance falhou")
    print("Bybit:", len(get_bybit_candles(SYMBOL, INTERVAL, 1)) if get_bybit_candles(SYMBOL, INTERVAL, 1) else "Bybit falhou")
    
    # Inicia aplicação
    Thread(target=trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=8000)
