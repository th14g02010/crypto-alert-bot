import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')  # Símbolo mais líquido
INTERVAL = os.getenv('INTERVAL', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== FUNÇÕES DE API ==================
def get_binance_candles(symbol, interval, limit=21):
    """Obtém candles da Binance com tratamento completo"""
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            },
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        
        if response.status_code == 200:
            return [{
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "time": datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d %H:%M'),
                "source": "Binance"
            } for candle in response.json()]
    
    except Exception as e:
        print(f"Binance API Error: {str(e)[:100]}")
    return None

def get_bybit_candles(symbol, interval, limit=21):
    """Fallback para Bybit com tratamento robusto"""
    try:
        # Converte intervalos (1h → 60)
        interval_map = {'1h': '60', '4h': '240', '1d': 'D'}
        bybit_interval = interval_map.get(interval, '60')
        
        response = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": str(limit)
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result", {}).get("list"):
                return [{
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "time": datetime.fromtimestamp(int(candle["startTime"])/1000).strftime('%Y-%m-%d %H:%M'),
                    "source": "Bybit"
                } for candle in data["result"]["list"]]
    
    except Exception as e:
        print(f"Bybit API Error: {str(e)[:100]}")
    return None

def get_market_data():
    """Obtém dados com fallback automático"""
    print("\n🔍 Buscando dados do mercado...")
    
    # Tenta Binance primeiro
    data = get_binance_candles(SYMBOL, INTERVAL)
    if data:
        print(f"✅ Dados obtidos da Binance ({len(data)} candles)")
        return data
    
    # Fallback para Bybit
    print("🔁 Binance falhou, tentando Bybit...")
    data = get_bybit_candles(SYMBOL, INTERVAL)
    if data:
        print(f"✅ Dados obtidos da Bybit ({len(data)} candles)")
        return data
    
    print("❌ Todas as APIs falharam")
    return None

# ================== LÓGICA DO BOT ==================
def send_alert(message):
    """Envia alertas para o Telegram"""
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print("⚠️ Configurações do Telegram ausentes")
            return False
            
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=5
        )
        print("📤 Alerta enviado")
        return True
    except Exception as e:
        print(f"⚠️ Erro no Telegram: {str(e)[:100]}")
        return False

def analyze_market():
    """Executa análise e envia alertas"""
    data = get_market_data()
    if not data:
        return False
    
    last_candle = data[-1]
    price_change = ((last_candle['close'] - data[-2]['close']) / data[-2]['close']) * 100
    
    message = (
        f"📊 **{SYMBOL} {INTERVAL} Update**\n"
        f"⏰ {last_candle['time']}\n"
        f"💰 Preço: ${last_candle['close']:.2f}\n"
        f"📈 Variação: {price_change:+.2f}%\n"
        f"🔍 Fonte: {last_candle['source']}"
    )
    
    return send_alert(message)

def trading_loop():
    """Loop principal com logging detalhado"""
    print("\n🔄 Iniciando loop de trading...")
    cycle = 0
    
    while True:
        cycle += 1
        start_time = time.time()
        
        try:
            print(f"\n♻️ Ciclo #{cycle} | {datetime.now().strftime('%H:%M:%S')}")
            
            if analyze_market():
                print("✅ Análise concluída")
            else:
                print("⚠️ Falha na análise")
            
            # Calcula tempo restante do intervalo
            elapsed = time.time() - start_time
            sleep_time = max(CHECK_INTERVAL - elapsed, 5)
            print(f"⏳ Próxima verificação em {sleep_time:.0f}s")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"🔥 Erro crítico: {str(e)}")
            time.sleep(60)

# ================== WEB SERVICE ==================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Crypto Trading Bot",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({"healthy": True, "time": datetime.now().isoformat()})

# ================== INICIALIZAÇÃO ==================
if __name__ == "__main__":
    # Configuração inicial
    print("\n" + "="*50)
    print(f"🚀 Iniciando Crypto Bot - {datetime.now().strftime('%d/%m %H:%M')}")
    print(f"📈 Par: {SYMBOL} | Intervalo: {INTERVAL}")
    print(f"🔄 Ciclo: {CHECK_INTERVAL//60} minutos")
    print("="*50 + "\n")
    
    # Teste inicial das APIs
    print("⚙️ Testando conexões...")
    print(f"Binance: {'✅' if get_binance_candles(SYMBOL, INTERVAL, 1) else '❌'}")
    print(f"Bybit: {'✅' if get_bybit_candles(SYMBOL, INTERVAL, 1) else '❌'}")
    
    # Inicia o bot
    Thread(target=trading_loop, daemon=True).start()
    
    # Inicia o Flask
    app.run(host='0.0.0.0', port=8000, use_reloader=False)
