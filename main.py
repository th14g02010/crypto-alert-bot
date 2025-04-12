import os
import requests
import time
import logging
from datetime import datetime
from threading import Thread, Lock
from flask import Flask, jsonify

# Configurações
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SYMBOL = os.getenv('SYMBOL', 'BTC-USDT')
INTERVAL = os.getenv('INTERVAL', '1hour')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '1800'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Configuração de logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
data_lock = Lock()
last_signal = None
monitoring_data = {
    'cycles': 0,
    'errors': 0,
    'signals_detected': 0,
    'last_checked': None
}

# ================== FUNÇÕES DA API ==================
def get_candles(symbol=SYMBOL, interval=INTERVAL, limit=50):
    """Obtém dados da KuCoin com logging detalhado"""
    with data_lock:
        monitoring_data['cycles'] += 1
        
    try:
        logger.info(f"Buscando candles: {symbol} {interval}")
        start_time = time.time()
        
        url = "https://api.kucoin.com/api/v1/market/candles"
        params = {
            "symbol": symbol,
            "type": interval,
            "limit": limit
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data['code'] != '200000':
            logger.error(f"Erro na API: {data.get('msg', 'Erro desconhecido')}")
            return None

        processing_time = time.time() - start_time
        logger.debug(f"Dados recebidos em {processing_time:.2f}s - {len(data['data'])} candles")
        
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

        with data_lock:
            monitoring_data['last_checked'] = datetime.now().isoformat()

        return candles[::-1]

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede: {str(e)}", exc_info=True)
        with data_lock:
            monitoring_data['errors'] += 1
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        with data_lock:
            monitoring_data['errors'] += 1
    
    return None

# ================== ANÁLISE TÉCNICA ==================
def detect_engulfing(candles):
    """Detecção de padrões com logging"""
    try:
        if len(candles) < 2:
            return None

        prev = candles[-2]
        current = candles[-1]

        bull_conditions = (
            prev['close'] < prev['open'] and
            current['close'] > current['open'] and
            current['close'] > prev['open'] and
            current['open'] < prev['close']
        )

        bear_conditions = (
            prev['close'] > prev['open'] and
            current['close'] < current['open'] and
            current['open'] > prev['close'] and
            current['close'] < prev['open']
        )

        if bull_conditions:
            logger.info("Padrão Bullish Engulfing detectado")
            return 'bullish'
        if bear_conditions:
            logger.info("Padrão Bearish Engulfing detectado")
            return 'bearish'
            
    except Exception as e:
        logger.error(f"Erro na detecção de padrões: {str(e)}", exc_info=True)
    
    return None

# ================== SISTEMA DE ALERTAS ==================
def send_alert(signal_type, entry_price, trend):
    """Envio de alertas com tracking"""
    global last_signal
    
    try:
        if signal_type == last_signal:
            logger.debug("Sinal repetido - alerta ignorado")
            return False

        # Cálculo de TP/SL
        if signal_type == 'bullish':
            tp = entry_price * 1.03
            sl = entry_price * 0.985
            emoji = '🚀'
            direction = 'ALTA'
        else:
            tp = entry_price * 0.97
            sl = entry_price * 1.015
            emoji = '⚠️'
            direction = 'BAIXA'

        message = (
            f"{emoji} **ALERTA {direction}**\n\n"
            f"• Par: {SYMBOL.replace('-', '/')}\n"
            f"• Timeframe: {INTERVAL}\n"
            f"• Hora: {datetime.now().strftime('%d/%m %H:%M:%S')}\n\n"
            f"💰 Entrada: ${entry_price:.2f}\n"
            f"🎯 TP: ${tp:.2f}\n"
            f"🛑 SL: ${sl:.2f}\n\n"
            f"📈 Tendência: {trend.upper()}"
        )

        start_time = time.time()
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10
        )
        
        response_time = time.time() - start_time
        logger.info(f"Alerta enviado em {response_time:.2f}s - Status: {response.status_code}")

        if response.status_code == 200:
            with data_lock:
                last_signal = signal_type
                monitoring_data['signals_detected'] += 1
            return True

    except Exception as e:
        logger.error(f"Falha no envio do alerta: {str(e)}", exc_info=True)
        with data_lock:
            monitoring_data['errors'] += 1
    
    return False

# ================== MONITORAMENTO ==================
@app.route('/status')
def get_status():
    """Endpoint de monitoramento detalhado"""
    with data_lock:
        return jsonify({
            'status': 'online',
            'ultimo_sinal': last_signal,
            'monitoramento': monitoring_data,
            'config': {
                'symbol': SYMBOL,
                'interval': INTERVAL,
                'check_interval': CHECK_INTERVAL
            }
        })

@app.route('/logs')
def get_logs():
    """Últimas 100 linhas de logs"""
    try:
        with open('trading_bot.log', 'r') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================== LÓGICA PRINCIPAL ==================
def trading_cycle():
    logger.info("Iniciando ciclo de trading...")
    while True:
        try:
            candles = get_candles()
            if candles:
                signal = detect_engulfing(candles)
                if signal:
                    trend = get_trend(candles)
                    send_alert(signal, candles[-1]['close'], trend)
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.critical(f"Erro crítico no ciclo: {str(e)}", exc_info=True)
            time.sleep(60)

if __name__ == '__main__':
    logger.info("""
    ====================================
        INICIANDO BOT DE TRADING
        Par: %s
        Intervalo: %s
        Check a cada: %ss
    ====================================
    """, SYMBOL, INTERVAL, CHECK_INTERVAL)
    
    Thread(target=trading_cycle, daemon=True).start()
    app.run(host='0.0.0.0', port=8000)
