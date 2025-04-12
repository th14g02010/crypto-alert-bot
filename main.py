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

# ========== FUNÇÕES DO BOT ==========
def get_candles():
    """Versão simplificada apenas para teste"""
    return [{
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "source": "Simulado"
    }]

def send_telegram_alert(message):
    """Versão simplificada para teste"""
    print(f"📤 Mensagem simulada para Telegram: {message[:50]}...")
    return True

def trading_loop():
    """Loop principal com logging aprimorado"""
    print("\n🔄 Iniciando loop de trading...")
    counter = 0
    
    while True:
        try:
            counter += 1
            print(f"\n🔁 Ciclo #{counter} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Simula análise de mercado
            candles = get_candles()
            if candles:
                last_price = candles[-1]['close']
                print(f"📊 Preço simulado: {last_price}")
                
                if counter % 3 == 0:  # Envia alerta a cada 3 ciclos
                    msg = f"Teste #{counter} | Preço: {last_price}"
                    send_telegram_alert(msg)
            
            time.sleep(10)  # Intervalo reduzido para testes
            
        except Exception as e:
            print(f"⚠️ Erro no ciclo {counter}: {str(e)}")
            time.sleep(30)

# ========== ROTAS FLASK ==========
@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "service": "Bot de Trading",
        "last_activity": datetime.now().isoformat()
    })

@app.route('/status')
def status():
    return jsonify({
        "running": True,
        "symbol": SYMBOL,
        "interval": INTERVAL
    })

# ========== INICIALIZAÇÃO ==========
if __name__ == "__main__":
    # Configuração inicial
    print("="*50)
    print(f"🤖 Iniciando Bot de Trading - {datetime.now().strftime('%d/%m %H:%M')}")
    print(f"📈 Par: {SYMBOL} | Intervalo: {INTERVAL}")
    print(f"🔄 Verificação a cada: {CHECK_INTERVAL//60} minutos")
    print("="*50)
    
    # Inicia o bot em thread separada
    bot_thread = Thread(target=trading_loop, daemon=True)
    bot_thread.start()
    print("✅ Thread do bot iniciada")
    
    # Inicia o servidor Flask
    print("🌐 Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=8000)
