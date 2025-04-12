import requests
import time

TELEGRAM_TOKEN = "7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM"
CHAT_ID = "6197066344"

last_signal = None  # evitar alertas duplicados

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar alerta Telegram: {e}")

def get_candles(symbol="SOLUSDT", interval="1h", limit=21):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return [
                {
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4])
                } for c in data
            ]
        else:
            raise ValueError("Resposta inesperada da API")
    except Exception as e:
        print(f"Erro ao obter candles: {e}")
        return []

def get_trend(candles):
    closes = [c["close"] for c in candles[:-1]]
    if len(closes) < 20:
        return "indefinida"
    avg_old = sum(closes[:10]) / 10
    avg_new = sum(closes[10:]) / 10
    return "up" if avg_new > avg_old else "down"

def detect_engulfing(c1, c2, type="bullish"):
    if type == "bullish":
        return c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["open"] and c2["open"] < c1["close"]
    elif type == "bearish":
        return c1["close"] > c1["open"] and c2["close"] < c2["open"] and c2["open"] > c1["close"] and c2["close"] < c1["open"]
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
                entry = round(current_price, 2)
                tp = round(entry * 1.03, 2)
                sl = round(entry * 0.985, 2)
                msg = f"""🚨 [ALERTA] Engolfo de Alta detectado em SOL/USDT (1H)

🟢 Tipo de entrada: Compra
💰 Preço de entrada: ${entry}
🎯 Take Profit (TP): ${tp} (+3%)
🛡️ Stop Loss (SL): ${sl} (-1.5%)

📊 Tendência principal: {trend_text}"""
                send_telegram_alert(msg)
                last_signal = "bullish"

            # Engolfo de Baixa
            elif detect_engulfing(c1, c2, "bearish") and last_signal != "bearish":
                msg = f"""⚠️ [ALERTA] Engolfo de Baixa detectado em SOL/USDT (1H)

🔴 Tipo de sinal: Reversão de alta ou saída
💸 Preço atual: ${round(current_price, 2)}
📊 Tendência principal: {trend_text}"""
                send_telegram_alert(msg)
                last_signal = "bearish"

        except Exception as e:
            print("Erro na análise ou envio:", e)

        time.sleep(1800)

if __name__ == "__main__":
    print("Bot de alerta SOL/USDT iniciado...")
    main_loop()
