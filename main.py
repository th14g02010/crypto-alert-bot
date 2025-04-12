import os
import requests
import random
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
INTERVAL = os.getenv('INTERVAL', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== LISTA DE PROXIES GRATUITOS ==================
# Fonte: https://free-proxy-list.net/ (atualize regularmente)
PROXY_LIST = [
    {"http": "http://45.79.199.106:80", "https": "http://45.79.199.106:80", "country": "us"},
    {"http": "http://45.56.92.196:80", "https": "http://45.56.92.196:80", "country": "us"},
    {"http": "http://45.33.81.195:80", "https": "http://45.33.81.195:80", "country": "us"},
    {"http": "http://45.33.16.64:80", "https": "http://45.33.16.64:80", "country": "us"},
    {"http": "http://45.33.105.35:80", "https": "http://45.33.105.35:80", "country": "us"},
    # Adicione mais proxies aqui (máx 10 para evitar lentidão)
]

def get_random_proxy():
    """Seleciona um proxy aleatório da lista"""
    return random.choice(PROXY_LIST)

def test_proxy(proxy):
    """Testa se um proxy está funcionando"""
    try:
        test_url = "https://api.binance.com/api/v3/ping"
        response = requests.get(test_url, proxies=proxy, timeout=10)
        return response.status_code == 200
    except:
        return False

def refresh_proxies():
    """Atualiza a lista de proxies (simplificado)"""
    global PROXY_LIST
    try:
        response = requests.get("https://free-proxy-list.net/")
        # Aqui você precisaria implementar um parser HTML para extrair os proxies
        # Esta é apenas uma estrutura básica
        print("⚠️ Implemente o parser de proxies aqui")
        return PROXY_LIST  # Mantém a lista atual como fallback
    except:
        return PROXY_LIST

# ================== FUNÇÕES DE API COM PROXIES ==================
def make_api_request(url, params=None, max_retries=3):
    """Faz requisições com tentativas através de proxies diferentes"""
    for attempt in range(max_retries):
        proxy = get_random_proxy()
        print(f"🔁 Tentativa {attempt + 1} via proxy {proxy['http']} ({proxy['country']})")
        
        try:
            response = requests.get(
                url,
                params=params,
                proxies=proxy,
                timeout=15
            )
            
            if response.status_code == 200:
                return response
                
        except Exception as e:
            print(f"❌ Falha no proxy: {str(e)[:50]}")
            time.sleep(1)
    
    print("⚠️ Todas as tentativas com proxies falharam")
    return None

def get_binance_candles(symbol, interval, limit=21):
    """Obtém candles da Binance usando proxies"""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    response = make_api_request(url, params)
    if response:
        try:
            return [{
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "time": datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d %H:%M'),
                "source": "Binance"
            } for candle in response.json()]
        except Exception as e:
            print(f"Erro ao processar dados: {str(e)}")
    
    return None

def get_bybit_candles(symbol, interval, limit=21):
    """Fallback para Bybit quando Binance falha"""
    try:
        interval_map = {'1h': '60', '4h': '240', '1d': 'D'}
        response = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol,
                "interval": interval_map.get(interval, '60'),
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

# ================== CORE DO BOT ==================
def send_telegram_alert(message):
    """Envia mensagens para o Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Configurações do Telegram ausentes")
        return False
        
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Erro no Telegram: {str(e)[:50]}")
        return False

def analyze_market():
    """Executa análise de mercado"""
    print("\n🔍 Analisando mercado...")
    
    # Tenta Binance com proxies primeiro
    candles = get_binance_candles(SYMBOL, INTERVAL)
    
    # Fallback para Bybit se necessário
    if not candles:
        print("🔁 Binance falhou, tentando Bybit...")
        candles = get_bybit_candles(SYMBOL, INTERVAL)
    
    if candles:
        last_candle = candles[-1]
        price_change = ((last_candle['close'] - candles[-2]['close']) / candles[-2]['close']) * 100
        
        message = (
            f"📊 **{SYMBOL} {INTERVAL} Update**\n"
            f"⏰ {last_candle['time']}\n"
            f"💰 Preço: ${last_candle['close']:.2f}\n"
            f"📈 Variação: {price_change:+.2f}%\n"
            f"🔍 Fonte: {last_candle['source']}"
        )
        
        if send_telegram_alert(message):
            print("✅ Alerta enviado")
            return True
    
    print("❌ Falha na análise do mercado")
    return False

def trading_loop():
    """Loop principal do bot"""
    print("\n🤖 Iniciando bot de trading...")
    cycle = 0
    
    while True:
        cycle += 1
        print(f"\n♻️ Ciclo #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Atualiza proxies a cada 10 ciclos
            if cycle % 10 == 0:
                refresh_proxies()
            
            if analyze_market():
                print("✅ Ciclo concluído com sucesso")
            else:
                print("⚠️ Problemas neste ciclo")
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"🔥 Erro crítico: {str(e)}")
            time.sleep(60)

# ================== WEB SERVICE ==================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Crypto Trading Bot",
        "proxy_count": len(PROXY_LIST),
        "last_check": datetime.now().isoformat()
    })

@app.route('/proxies')
def list_proxies():
    return jsonify({
        "proxies": PROXY_LIST,
        "working": [test_proxy(p) for p in PROXY_LIST]
    })

# ================== INICIALIZAÇÃO ==================
if __name__ == "__main__":
    # Teste inicial dos proxies
    print("⚙️ Testando proxies...")
    working_proxies = [p for p in PROXY_LIST if test_proxy(p)]
    print(f"✅ {len(working_proxies)}/{len(PROXY_LIST)} proxies funcionando")
    
    # Inicia o bot em thread separada
    Thread(target=trading_loop, daemon=True).start()
    
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=8000, use_reloader=False)
