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

# Variáveis de estado
last_signal = None

# ================== FUNÇÕES DE ANÁLISE ==================
def detect_engulfing(candles):
    """Detecta padrões de engulfing de alta/baixa"""
    if len(candles) < 2:
        return None
    
    prev_candle = candles[-2]
    current_candle = candles[-1]
    
    # Calcula o tamanho dos corpos
    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    current_body = abs(current_candle['close'] - current_candle['open'])
    
    # Engulfing de Alta (Bearish para Bullish)
    if (prev_candle['close'] < prev_candle['open'] and  # Vela anterior de baixa
        current_candle['close'] > current_candle['open'] and  # Vela atual de alta
        current_body >= 1.5 * prev_body and  # Corpo pelo menos 50% maior
        current_candle['close'] > prev_candle['open'] and  # Engolfa alta
        current_candle['open'] < prev_candle['close']):
        
        return 'bullish'
    
    # Engulfing de Baixa (Bullish para Bearish)
    elif (prev_candle['close'] > prev_candle['open'] and  # Vela anterior de alta
          current_candle['close'] < current_candle['open'] and  # Vela atual de baixa
          current_body >= 1.5 * prev_body and  # Corpo pelo menos 50% maior
          current_candle['open'] > prev_candle['close'] and  # Engolfa baixa
          current_candle['close'] < prev_candle['open']):
        
        return 'bearish'
    
    return None

def get_trend(candles, period=20):
    """Determina a tendência usando média móvel"""
    if len(candles) < period:
        return 'neutral'
    
    closes = [c['close'] for c in candles[-period:]]
    sma = sum(closes) / period
    current_price = candles[-1]['close']
    
    if current_price > sma * 1.02:  # 2% acima da média
        return 'alta'
    elif current_price < sma * 0.98:  # 2% abaixo da média
        return 'baixa'
    return 'lateral'

def calculate_price_levels(entry_price, signal_type):
    """Calcula TP/SL com base no tipo de sinal"""
    if signal_type == 'bullish':
        tp = entry_price * 1.03  # +3%
        sl = entry_price * 0.985  # -1.5%
    elif signal_type == 'bearish':
        tp = entry_price * 0.97  # -3%
        sl = entry_price * 1.015  # +1.5%
    else:
        return None, None
    
    return round(tp, 4), round(sl, 4)

# ================== LÓGICA DO BOT ==================
def send_alert(signal_type, entry_price, trend):
    """Envia alerta formatado para o Telegram"""
    global last_signal
    
    if signal_type == last_signal:
        return False
    
    tp, sl = calculate_price_levels(entry_price, signal_type)
    
    emoji = '🚀' if signal_type == 'bullish' else '⚠️'
    action = 'COMPRA' if signal_type == 'bullish' else 'VENDA'
    
    message = (
        f"{emoji} **ALERTA DE TRADING** {emoji}\n\n"
        f"🏷️ **Par:** {SYMBOL.replace('-', '/')}\n"
        f"⏰ **Horário:** {datetime.now().strftime('%d/%m %H:%M')}\n"
        f"🔍 **Padrão:** Engolfo de {signal_type.upper()}\n"
        f"📈 **Tendência:** {trend.upper()}\n\n"
        f"💵 **Entrada:** ${entry_price:.4f}\n"
        f"🎯 **Take Profit:** ${tp:.4f}\n"
        f"🛑 **Stop Loss:** ${sl:.4f}\n\n"
        f"📊 **Intervalo:** {INTERVAL}\n"
        f"🔔 **Fonte:** KuCoin API"
    )
    
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
        
        if response.status_code == 200:
            last_signal = signal_type
            return True
    except Exception as e:
        print(f"Erro no Telegram: {str(e)}")
    
    return False

def analyze_market():
    """Executa análise completa do mercado"""
    candles = get_candles()
    if not candles or len(candles) < 20:
        return False
    
    # Detecta padrões
    engulfing_signal = detect_engulfing(candles)
    trend = get_trend(candles)
    
    if engulfing_signal:
        entry_price = candles[-1]['close']
        return send_alert(engulfing_signal, entry_price, trend)
    
    return False

# ================== FUNÇÕES DA API KUCOIN ==================
def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=50):
    """Obtém candles da KuCoin (mantido do código anterior)"""
    try:
        # ... (implementação idêntica à versão anterior)
        # Retorna lista de candles formatados
    except Exception as e:
        print(f"Erro na API: {str(e)}")
        return None

# ... (mantenha as outras funções e inicialização idênticas ao código anterior)

if __name__ == "__main__":
    # ... (código de inicialização idêntico)
