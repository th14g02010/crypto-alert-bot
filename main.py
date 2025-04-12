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
INTERVAL = os.getenv('INTERVAL', '1hour')  # KuCoin usa '1hour' em vez de '1h'
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)

# ================== FUNÇÕES DA API KUCOIN ==================
def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=21):
    """Obtém candles da KuCoin com monitoramento detalhado"""
    try:
        print(f"\n📡 Buscando dados da KuCoin... | Par: {symbol} | Intervalo: {interval}")
        start_time = time.time()
        
        url = "https://api.kucoin.com/api/v1/market/candles"
        params = {
            "symbol": symbol,
            "type": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=15)
        response_time = time.time() - start_time
        
        print(f"⏱️ Tempo de resposta: {response_time:.2f}s | Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "200000":
                candles = []
                for candle in data["data"]:
                    candles.append({
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "time": datetime.fromtimestamp(int(candle[0])).strftime('%Y-%m-%d %H:%M'),
                        "source": "KuCoin"
                    })
                print(f"✅ Dados recebidos: {len(candles)} candles")
                return candles[::-1]  # Inverte para ordem cronológica
            else:
                print(f"❌ Erro na API: {data.get('msg', 'Sem mensagem de erro')}")
        else:
            print(f"⚠️ Status code inválido: {response.status_code}")
            
    except Exception as e:
        print(f"🔥 Erro na requisição: {str(e)[:100]}")
    
    return None

# ================== LÓGICA DO BOT ==================
def send_alert(message):
    """Envia alertas para o Telegram com logging"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⛔ Telegram não configurado")
        return False
        
    try:
        print("\n✉️ Enviando alerta para Telegram...")
        start_time = time.time()
        
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        
        print(f"📨 Status: {response.status_code} | Tempo: {time.time() - start_time:.2f}s")
        return response.status_code == 200
        
    except Exception as e:
        print(f"⚠️ Falha no Telegram: {str(e)[:50]}")
        return False

def analyze_market():
    """Analisa o mercado com logging detalhado"""
    print("\n🔍 Iniciando análise de mercado...")
    analysis_start = time.time()
    
    candles = get_candles()
    if not candles or len(candles) < 2:
        print("⛔ Dados insuficientes para análise")
        return False
    
    last_candle = candles[-1]
    prev_candle = candles[-2]
    
    # Cálculos
    price_change = ((last_candle['close'] - prev_candle['close']) / prev_candle['close']) * 100
    candle_type = "🟢 Alta" if last_candle['close'] > last_candle['open'] else "🔴 Baixa"
    volume_change = ((last_candle['volume'] - prev_candle['volume']) / prev_candle['volume']) * 100
    
    # Construção da mensagem
    message = (
        f"📊 **{SYMBOL.replace('-', '/')} {INTERVAL}**\n"
        f"⏰ {last_candle['time']} | {candle_type}\n"
        f"💰 Preço: ${last_candle['close']:.4f}\n"
        f"📈 Variação: {price_change:+.2f}%\n"
        f"💨 Volume: {last_candle['volume']:.2f} ({volume_change:+.1f}%)\n"
        f"🔄 Fonte: KuCoin API"
    )
    
    # Envio do alerta
    alert_result = send_alert(message)
    print(f"⏳ Análise concluída em {time.time() - analysis_start:.2f}s")
    
    return alert_result

def trading_loop():
    """Loop principal com monitoramento detalhado"""
    print("\n🤖 Iniciando KuCoin Trading Bot")
    print(f"⚙️ Configuração:")
    print(f"• Par: {SYMBOL}")
    print(f"• Intervalo: {INTERVAL}")
    print(f"• Ciclo: {CHECK_INTERVAL//60} minutos\n")
    
    cycle = 0
    while True:
        cycle += 1
        cycle_start = time.time()
        
        try:
            print(f"\n♻️ CICLO #{cycle} | {datetime.now().strftime('%d/%m %H:%M:%S')}")
            
            if analyze_market():
                print("✅ Ciclo concluído com sucesso")
            else:
                print("⚠️ Problemas detectados neste ciclo")
            
            # Gerenciamento do tempo do ciclo
            elapsed = time.time() - cycle_start
            sleep_time = max(CHECK_INTERVAL - elapsed, 5)
            print(f"⏳ Próximo ciclo em {sleep_time:.0f}s")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"🔥 ERRO CRÍTICO: {str(e)}")
            print("🛑 Esperando 1 minuto antes de retomar...")
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
        "last_check": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "https://docs.kucoin.com"
        }
    })

@app.route('/health')
def health_check():
    """Endpoint avançado de health check"""
    test_start = time.time()
    
    # Teste da API
    api_status = False
    try:
        test_data = get_candles(limit=1)
        api_status = bool(test_data)
    except:
        pass
    
    # Teste do Telegram
    telegram_status = False
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            telegram_status = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
                timeout=5
            ).status_code == 200
        except:
            pass
    
    return jsonify({
        "healthy": api_status and telegram_status,
        "api_online": api_status,
        "telegram_online": telegram_status,
        "response_time_ms": int((time.time() - test_start) * 1000),
        "timestamp": datetime.now().isoformat()
    })

# ================== INICIALIZAÇÃO ==================
if __name__ == "__main__":
    # Banner de inicialização
    print("\n" + "=" * 50)
    print(f"🚀 INICIANDO KUCOIN TRADING BOT")
    print(f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50 + "\n")
    
    # Verificação inicial
    print("⚙️ Executando verificações iniciais...")
    print(f"• Testando conexão com KuCoin API...", end=" ")
    test_candles = get_candles(limit=1)
    print("✅ OK" if test_candles else "❌ FALHA")
    
    print(f"• Verificando Telegram...", end=" ")
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            telegram_test = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
                timeout=5
            ).status_code == 200
            print("✅ OK" if telegram_test else "❌ FALHA")
        except:
            print("⚠️ ERRO")
    else:
        print("⏭️ DESATIVADO")
    
    # Inicia serviços
    print("\n🔧 Iniciando serviços...")
    Thread(target=trading_loop, daemon=True).start()
    print("✅ Thread do trading iniciada")
    
    print("🌐 Iniciando servidor web...")
    app.run(host='0.0.0.0', port=8000, use_reloader=False)
