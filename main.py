import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTC-USDT')  # Formato KuCoin
INTERVAL = os.getenv('INTERVAL', '1hour')  # Valores corretos: 1min, 5min, 15min, 30min, 1hour, 6hour, 1day
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== FUNÇÕES DA API KUCOIN ==================
def get_valid_intervals():
    """Retorna os intervalos válidos para a KuCoin API"""
    return {
        '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min',
        '1h': '1hour', '2h': '2hour', '4h': '4hour', '6h': '6hour', '12h': '12hour',
        '1d': '1day', '1w': '1week'
    }

def normalize_interval(interval):
    """Converte intervalos comuns para o formato KuCoin"""
    interval_map = get_valid_intervals()
    return interval_map.get(interval.lower(), interval)

def verify_symbol(symbol):
    """Verifica se o símbolo está no formato correto (ex: BTC-USDT)"""
    if '-' not in symbol:
        print(f"⚠️ Símbolo {symbol} não está no formato KuCoin (MOEDA-BASE)")
        return symbol.replace('/', '-') if '/' in symbol else f"{symbol}-USDT"
    return symbol

def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém candles da KuCoin com tratamento robusto de erros"""
    try:
        # Normaliza os parâmetros
        symbol = verify_symbol(symbol)
        interval = normalize_interval(interval)
        
        print(f"\n📡 Buscando {limit} candles de {symbol} no intervalo {interval}")
        
        url = "https://api.kucoin.com/api/v1/market/candles"
        params = {
            "symbol": symbol,
            "type": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Tratamento específico para erros da KuCoin
        if data.get("code") != "200000":
            error_msg = data.get("msg", "Erro desconhecido")
            if "Incorrect candlestick type" in error_msg:
                print(f"❌ Intervalo inválido: {interval}. Use: {', '.join(get_valid_intervals().values())}")
            else:
                print(f"❌ Erro na API: {error_msg}")
            return None
            
        if not data.get("data"):
            print("⚠️ Nenhum dado retornado pela API")
            return None
            
        candles = []
        for candle in data["data"]:
            try:
                candles.append({
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                    "time": datetime.fromtimestamp(int(candle[0])).strftime('%Y-%m-%d %H:%M'),
                    "source": "KuCoin"
                })
            except (IndexError, ValueError) as e:
                print(f"⚠️ Erro ao processar candle: {str(e)}")
                continue
                
        print(f"✅ {len(candles)} candles obtidos com sucesso")
        return candles[::-1]  # Inverte para ordem cronológica
        
    except requests.exceptions.RequestException as e:
        print(f"🌐 Erro na requisição: {str(e)[:100]}")
    except Exception as e:
        print(f"🔥 Erro inesperado: {str(e)}")
        
    return None

# ================== LÓGICA DO BOT ==================
def send_alert(message):
    """Envia alertas para o Telegram com tratamento de erros"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⛔ Telegram não configurado - alerta não enviado")
        return False
        
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Erro no Telegram: {str(e)[:50]}")
        return False

def analyze_market():
    """Analisa o mercado com tratamento robusto"""
    print("\n🔍 Iniciando análise de mercado...")
    start_time = time.time()
    
    candles = get_candles()
    if not candles or len(candles) < 2:
        print("⛔ Dados insuficientes para análise")
        return False
        
    last_candle = candles[-1]
    prev_candle = candles[-2]
    
    # Cálculos com tratamento de divisão por zero
    try:
        price_change_pct = ((last_candle['close'] - prev_candle['close']) / prev_candle['close']) * 100
        volume_change_pct = ((last_candle['volume'] - prev_candle['volume']) / prev_candle['volume']) * 100
    except ZeroDivisionError:
        price_change_pct = 0
        volume_change_pct = 0
    
    # Formatação dos valores
    price_change_str = f"+{price_change_pct:.2f}%" if price_change_pct >= 0 else f"{price_change_pct:.2f}%"
    volume_change_str = f"+{volume_change_pct:.1f}%" if volume_change_pct >= 0 else f"{volume_change_pct:.1f}%"
    
    message = (
        f"📊 **{SYMBOL.replace('-', '/')} {INTERVAL}**\n"
        f"⏰ {last_candle['time']}\n"
        f"💰 Preço: ${last_candle['close']:.4f} ({price_change_str})\n"
        f"📈 Volume: {last_candle['volume']:.2f} ({volume_change_str})\n"
        f"🔍 Fonte: KuCoin API"
    )
    
    if send_alert(message):
        print(f"✅ Análise concluída em {time.time() - start_time:.2f}s")
        return True
    
    print("⛔ Falha ao enviar alerta")
    return False

def trading_loop():
    """Loop principal com monitoramento detalhado"""
    print("\n🤖 Iniciando KuCoin Trading Bot")
    print(f"⚙️ Configuração atual:")
    print(f"• Par: {SYMBOL}")
    print(f"• Intervalo: {INTERVAL}")
    print(f"• Ciclo: {CHECK_INTERVAL//60} minutos")
    
    cycle = 0
    while True:
        cycle += 1
        cycle_start = time.time()
        
        try:
            print(f"\n♻️ CICLO #{cycle} | {datetime.now().strftime('%d/%m %H:%M:%S')}")
            
            if analyze_market():
                print("✅ Análise concluída com sucesso")
            else:
                print("⚠️ Problemas na análise")
            
            elapsed = time.time() - cycle_start
            sleep_time = max(CHECK_INTERVAL - elapsed, 5)
            print(f"⏳ Próximo ciclo em {sleep_time:.0f}s")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"🔥 ERRO CRÍTICO: {str(e)}")
            print("🛑 Esperando 60 segundos antes de retomar...")
            time.sleep(60)

# ================== WEB SERVICE ==================
@app.route('/')
def status():
    """Endpoint de status com informações detalhadas"""
    return jsonify({
        "status": "operacional",
        "exchange": "KuCoin",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "valid_intervals": list(get_valid_intervals().values()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Endpoint avançado de health check"""
    test_start = time.time()
    
    # Teste da API
    api_test = get_candles(limit=1) is not None
    
    # Teste do Telegram
    telegram_test = False
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            telegram_test = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
                timeout=5
            ).status_code == 200
        except:
            pass
    
    return jsonify({
        "healthy": api_test and telegram_test,
        "api_online": api_test,
        "telegram_online": telegram_test,
        "response_time_ms": int((time.time() - test_start) * 1000),
        "timestamp": datetime.now().isoformat()
    })

# ================== INICIALIZAÇÃO ==================
if __name__ == "__main__":
    # Banner de inicialização
    print("\n" + "=" * 50)
    print(f"🚀 KUCOIN TRADING BOT")
    print(f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    
    # Verificação inicial
    print("\n⚙️ Executando verificações iniciais...")
    print(f"• Testando conexão com KuCoin API...", end=" ")
    test_candles = get_candles(limit=1)
    print("✅ OK" if test_candles else "❌ FALHA")
    
    print(f"• Verificando Telegram...", end=" ")
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            telegram_test = req
