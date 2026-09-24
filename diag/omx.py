import yfinance as yf, pandas as pd
pd.set_option("display.width", 200)
print("yfinance", yf.__version__)
for t in ["^OMX", "^GDAXI", "^STOXX50E", "^GSPC"]:
    d = yf.download(t, start="2026-09-10", end="2026-09-25", interval="1d", auto_adjust=False, progress=False)
    print("\n=====", t, "DAGLIG, index-tz:", getattr(d.index, "tz", None))
    print(d["Close"].tail(8).to_string())
    h = yf.Ticker(t).history(period="5d", interval="1h", auto_adjust=False)
    print("---", t, "TIMDATA, tz:", h.index.tz, "rader:", len(h))
    print(h["Close"].tail(20).to_string())
    info = yf.Ticker(t).fast_info
    try: print("fast_info previous_close", info["previousClose"], "last_price", info["lastPrice"])
    except Exception as e: print("fast_info", e)
