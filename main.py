def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém candles com tratamento robusto de erros"""
    BASE_URLS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    for base_url in BASE_URLS:
        try:
            response = requests.get(
                f"{base_url}/api/v3/klines",
                headers=headers,
                params=params,
                timeout=15
            )
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
            print(f"Erro ao acessar {base_url}: {str(e)[:100]}...")
            continue
    
    print("❌ Todas as APIs falharam")
    return []
