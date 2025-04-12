import requests
import time
from decimal import Decimal  # Usar Decimal para precisão numérica

TELEGRAM_TOKEN = "7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM"
CHAT_ID = "6197066344"

last_signal = None

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar alerta Telegram: {e}")

def get_candles(symbol="SOL-USDT", interval="1hour", limit=21):
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {"symbol": symbol, "type": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "200000" and isinstance(data.get("data"), list):
            candles_data = data["data"]
            candles_data.reverse()  # KuCoin retorna candles mais recentes primeiro; invertemos
            return [
                {
                    "open": Decimal(c[1]),
                    "high": Decimal(c[2]),
                    "low": Decimal(c[3]),
                    "close": Decimal(c[4])
                } for c in candles_data
            ]
        else:
            raise ValueError(f"Resposta inválida da KuCoin: {data.get('msg')}")
    except Exception as e:
        print(f"Erro ao obter candles: {e}")
        return []

def get_trend(candles):
    closes = [c["close"] for c in candles[:-1]]
    if len(closes) < 20:
        return "indefinida"
    avg_old = sum(closes[:10]) / Decimal(10)
    avg_new = sum(closes[10:]) / Decimal(10)
    return "up" if avg_new > avg_old else "down"

def detect_engulfing(c1, c2, type="bullish"):
    if type == "bullish":
        return (c1["close"] < c1["open"] and 
                c2["close"] > c2["open"] and 
                c2["close"] > c1["open"] and 
                c2["open"] < c1["close"])
    elif type == "bearish":
        return (c1["close"] > c1["open"] and 
                c2["close"] < c2["open"] and 
                c2["open"] > c1["close"] and 
                c2["close"] < c1["open"])
    return False

def main_loop():
    global last_signal
    while True:
        candles = get_candles()
        if len(candles) < 2:
            print("Não foi possível obter candles suficientes.")
            time.sleep(1800)
            continue

        trend = get_trend(candles)
        trend_text = "🔺 Alta" if trend == "up" else "🔻 Baixa" if trend == "down" else "❓ Indefinida"

        c1 = candles[-2]
        c2 = candles[-1]
        current_price = c2["close"]

        try:
            # Engolfo de Alta
            if detect_engulfing(c1, c2, "bullish") and last_signal != "bullish":
                entry = current_price.quantize(Decimal("0.0001"))  # Ajuste conforme o tick size do ativo
                tp = (entry * Decimal("1.03")).quantize(Decimal("0.0001"))
                sl = (entry * Decimal("0.985")).quantize(Decimal("0.0001"))
                msg = f"""🚨 [ALERTA] Engolfo de Alta detectado em SOL/USDT (1H)

🟢 Tipo de entrada: Compra
💰 Preço de entrada: ${entry}
🎯 Take Profit (TP): ${tp} (+3%)
🛡️ Stop Loss (SL): ${sl} (-1.5
