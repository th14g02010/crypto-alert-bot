import os
import requests
import time
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTC-USDT')
INTERVAL = os.getenv('INTERVAL', '1hour')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))  # 30 minutos

app = Flask(__name__)
last_signal = None

# ================== FUNÇÕES DA API KUCOIN ==================
def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=50):
    """Obtém candles da KuCoin com tratamento completo de erros"""
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

        if data['code'] != '200000' or not data['data']:
            return None

        candles = []
        for c in data['data']:
            candles.append({
                'time': datetime.fromtimestamp(int(c[0])).strftime('%Y-%m-%d %H:%M'),
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5])
            })

        return candles[::-1]  # Ordenação cronológica correta

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {str(e)}")
    except Exception as e:
        print(f"Erro geral: {str(e)}")
    
    return None

# ================== ANÁLISE TÉCNICA ==================
def detect_engulfing(candles):
    """Detecta padrões de engulfing de alta/baixa"""
    if len(candles) < 2:
        return None

    prev = candles[-2]
    current = candles[-1]

    # Bullish Engulfing
    bull_conditions = (
        prev['close'] < prev['open'] and
        current['close'] > current['open'] and
        current['close'] > prev['open'] and
        current['open'] < prev['close']
    )

    # Bearish Engulfing
    bear_conditions = (
        prev['close'] > prev['open'] and
        current['close'] < current['open'] and
        current['open'] > prev['close'] and
        current['close'] < prev['open']
    )

    if bull_conditions:
        return 'bullish'
    if bear_conditions:
        return 'bearish'
    return None

def get_trend(candles, period=20):
    """Determina a tendência usando média móvel simples"""
    if len(candles) < period:
        return 'neutral'

    sma = sum(c['close'] for c in candles[-period:]) / period
    current = candles[-1]['close']

    if current > sma * 1.02:
        return 'alta'
    if current < sma * 0.98:
        return 'baixa'
    return 'lateral'

# ================== SISTEMA DE ALERTAS ==================
def send_alert(signal_type, entry_price, trend):
    """Envia alertas formatados para o Telegram"""
    global last_signal

    if signal_type == last_signal:
        return False

    # Cálculo dos níveis
    if signal_type == 'bullish':
        tp = entry_price * 1.03  # +3%
        sl = entry_price * 0.985  # -1.5%
    else:
        tp = entry_price * 0.97  # -3%
        sl = entry_price * 1.015  # +1.5%

    # Formatação da mensagem
    emoji = '🚀' if signal_type == 'bullish' else '⚠️'
    direction = 'ALTA' if signal_type == 'bullish' else 'BAIXA'
    
    message = (
        f"{emoji} **ALERTA DE ENGOLFO {direction}**\n\n"
        f"• Par: {SYMBOL.replace('-', '/')}\n"
        f"• Timeframe: {INTERVAL}\n"
        f"• Horário: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
        f"💰 Entrada: ${entry_price:.2f}\n"
        f"🎯 Take Profit: ${tp:.2f}\n"
        f"🛑 Stop Loss: ${sl:.2f}\n\n"
        f"📈 Tendência Atual: {trend.upper()}"
    )

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10
        )
        if response.status_code == 200:
            last_signal = signal_type
            return True
    except Exception as e:
        print(f"Erro no Telegram: {str(e)}")
    
    return False

# ================== LÓGICA PRINCIPAL ==================
def trading_cycle():
    """Loop principal de análise"""
    print("\n🤖 Bot iniciado. Pressione Ctrl+C para sair.")
    while True:
        try:
            candles = get_candles()
            if candles:
                signal = detect_engulfing(candles)
                if signal:
                    trend = get_trend(candles)
                    send_alert(signal, candles[-1]['close'], trend)
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 Bot interrompido")
            break
        except Exception as e:
            print(f"Erro no ciclo: {str(e)}")
            time.sleep(60)

# ================== WEB INTERFACE ==================
@app.route('/')
def status():
    return jsonify({
        'status': 'operacional',
        'par': SYMBOL,
        'timeframe': INTERVAL,
        'ultimo_sinal': last_signal,
        'ultima_verificacao': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({
        'online': True,
        'tempo_resposta': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Inicia o bot em thread separada
    Thread(target=trading_cycle, daemon=True).start()
    
    # Inicia o servidor web
    app.run(host='0.0.0.0', port=8000)
