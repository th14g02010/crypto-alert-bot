import requests
import time

TELEGRAM_TOKEN = "7851489296:AAGdtlr5tlRWtZQ4DGAFligu0lx7CQhjmkM"
CHAT_ID = "6197066344"

last_signal = None

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload, timeout=10)
        print(f"[INFO] Alerta enviado: {response.status_code}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar alerta Telegram: {e}")

def get_candles(symbol="SOL-USDT", interval="1hour", limit=21):
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {"symbol": symbol, "type": interval}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        if isinstance(data, list):
            candles = []
            for c in reversed(data[-limit:]):
                candles.append({
                    "open": float(c[1]),
                    "close": float(c[2]),
                    "high": float(c[3]),
                    "low": float(c[4])
                })
            print(f"[INFO] Candles obtidos: {len(candles)}")
            return candles
        else:
            raise ValueError("Resposta inesperada da API KuCoin")
    except Exception as e:
        print(f"[ERRO] Erro ao obter candles KuCoin: {e}")
        return []

def get_trend(candles):
    closes = [c["close"] for c in candles[:-1]]
    if len(closes) < 20:
        print("[AVISO] Candles insuficientes para calcular tendência")
        return "indefinida"
    avg_old = sum(closes[:10]) / 10
    avg_new = sum(closes[10:]) / 10
    trend = "up" if avg_new > avg_old else "down"
    print(f"[INFO] Tendência calculada: {trend}")
    return trend

def detect_engulfing(c1, c2, type="bullish"):
    if type == "bullish":
        return c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["open"] and c2["open"] < c1["close"]
    elif type == "bearish":
        return c1["close"] > c1["open"] and c2["close"] < c2["open"] and c2["open"] > c1["close"] and c2["close"] < c1["open"]
    return False

def main_loop():
    global last_signal
    while True:
        print("========================================")
        print("[CICLO] Verificando padrão em SOL/USDT...")
        candles = get_candles()
        if len(candles) < 2:
            print("[ERRO] Candles insuficientes, aguardando próximo ciclo...")
            time.sleep(1800)
            continue

        trend = get_trend(candles)
        trend_text = "Alta" if trend == "up" else "Baixa" if trend == "down" else "Indefinida"

        c1 = candles[-2]
        c2 = candles[-1]
        current_price = c2["close"]

        try:
            if detect_engulfing(c1, c2, "bullish"):
                print("[INFO] Padrão Engolfo de Alta detectado")
                if last_signal != "bullish":
                    entry = round(current_price, 2)
                    tp = round(entry * 1.03, 2)
                    sl = round(entry * 0.985, 2)
                    msg = f"[ALERTA] Engolfo de Alta detectado em SOL/USDT (1H)\n\nTipo de entrada: Compra\nPreço de entrada: ${entry}\nTake Profit (TP): ${tp} (+3%)\nStop Loss (SL): ${sl} (-1.5%)\n\nTendência principal: {trend_text}"
                    send_telegram_alert(msg)
                    last_signal = "bullish"
                else:
                    print("[INFO] Engolfo de Alta já foi sinalizado. Nenhum novo alerta.")

            elif detect_engulfing(c1, c2, "bearish"):
                print("[INFO] Padrão Engolfo de Baixa detectado")
                if last_signal != "bearish":
                    exit_price = round(current_price, 2)
                    tp = round(exit_price * 0.97, 2)
                    sl = round(exit_price * 1.015, 2)
                    msg = f"[ALERTA] Engolfo de Baixa detectado em SOL/USDT (1H)\n\nTipo de sinal: Saída ou venda\nPreço de saída: ${exit_price}\nAlvo de lucro: ${tp} (-3%)\nStop Loss: ${sl} (+1.5%)\n\nTendência principal: {trend_text}"
                    send_telegram_alert(msg)
                    last_signal = "bearish"
                else:
                    print("[INFO] Engolfo de Baixa já foi sinalizado. Nenhum novo alerta.")
            else:
                print("[INFO] Nenhum padrão engolfo identificado neste ciclo.")

        except Exception as e:
            print(f"[ERRO] Falha na análise ou envio: {e}")

        print("[INFO] Aguardando 30 minutos...\n")
        time.sleep(1800)

if __name__ == "__main__":
    print("[BOT] Bot de alerta SOL/USDT (KuCoin) iniciado...")
    main_loop()
