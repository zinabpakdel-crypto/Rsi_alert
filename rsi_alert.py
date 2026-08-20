import ccxt
import pandas as pd
import requests
import time
from datetime import datetime

# ==================== تنظیمات ====================
EITAA_TOKEN = "bot515564:c205f5be-7334-4070-baeb-97b57cd6623d"
EITAA_CHAT_ID = "11228587"

RSI_PERIOD = 14
TIMEFRAME = "30m"
CHECK_INTERVAL = 90
OVERSOLD = 20
OVERBOUGHT = 80
TOP_SYMBOLS_COUNT = 30
# ================================================

exchange = ccxt.kucoin({
    "enableRateLimit": True,
})

alerted = {}

def send_eitaa(text):
    url = f"https://eitaayar.ir/api/{EITAA_TOKEN}/sendMessage"
    payload = {
        "chat_id": EITAA_CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("پیام با موفقیت به ایتا ارسال شد")
        else:
            print("خطا در ارسال به ایتا:", response.text)
    except Exception as e:
        print("خطا در اتصال به ایتا:", e)

def get_top_symbols(limit=50):
    try:
        tickers = exchange.fetch_tickers()
        pairs = []
        for symbol, data in tickers.items():
            if symbol.endswith("/USDT") and data.get("quoteVolume"):
                pairs.append((symbol, float(data["quoteVolume"])))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in pairs[:limit]]
    except Exception as e:
        print("خطا در گرفتن لیست ارزها:", e)
        return []

def calculate_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_rsi(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        rsi_value = calculate_rsi(df["close"], RSI_PERIOD)
        return round(float(rsi_value), 2)
    except Exception as e:
        print(f"خطا در {symbol}: {e}")
        return None

def main():
    print("ربات مانیتورینگ RSI شروع به کار کرد (ایتا + KuCoin)...")
    send_eitaa("🚀 ربات مانیتورینگ RSI (۳۰ دقیقه) شروع به کار کرد\nصرافی: KuCoin\nپیام‌رسان: ایتا\nتعداد ارز: ۳۰")
    
    while True:
        try:
            symbols = get_top_symbols(TOP_SYMBOLS_COUNT)
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now}] در حال بررسی {len(symbols)} ارز...")

            for symbol in symbols:
                rsi = get_rsi(symbol)
                if rsi is None:
                    continue

                current_status = None
                if rsi <= OVERSOLD:
                    current_status = "oversold"
                elif rsi >= OVERBOUGHT:
                    current_status = "overbought"

                previous_status = alerted.get(symbol)

                if current_status and current_status != previous_status:
                    if current_status == "oversold":
                        emoji = "🟢"
                        status_text = "اشباع فروش (Oversold)"
                    else:
                        emoji = "🔴"
                        status_text = "اشباع خرید (Overbought)"

                    message = (
                        f"{emoji} {symbol}\n"
                        f"RSI (5m): {rsi}\n"
                        f"وضعیت: {status_text}\n"
                        f"زمان: {now}"
                    )
                    send_eitaa(message)
                    print(message)
                    alerted[symbol] = current_status

                elif not current_status and previous_status:
                    alerted[symbol] = None

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("خطای کلی در حلقه اصلی:", e)
            time.sleep(30)

if __name__ == "__main__":
    main()
