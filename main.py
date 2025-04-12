import os
import requests
import time
from datetime import datetime

# Configurações
SYMBOL = os.getenv('SYMBOL', 'SOLUSDT')
INTERVAL = os.getenv('INTERVAL', '1h')
API_URLS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com"
]

def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém candles com múltiplos fallbacks e headers personalizados"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    for base_url in API_URLS:
        try:
            response = requests.get(
                f"{base_url}/api/v3/klines",
                headers=headers,
                params=params,
                timeout=10
            )
            
            # Verifica se a resposta não é um HTML (bloqueio)
            if not response.text.strip().startswith('<!DOCTYPE html>'):
                response.raise_for_status()
                return [
                    {
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "time": datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M')
                    } for c in response.json() if len(c) >= 5
                ]
                
        except Exception as e:
            print(f"Tentativa com {base_url} falhou: {str(e)[:100]}")
            continue
    
    print("❌ Todas as APIs alternativas falharam")
    return []

# Exemplo de uso
if __name__ == "__main__":
    while True:
        candles = get_candles()
        if candles:
            print(f"Último candle: {candles[-1]['close']} | {candles[-1]['time']}")
        else:
            print("Aguardando reconexão...")
        time.sleep(60)
