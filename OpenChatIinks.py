import time
import webbrowser

# List of candlestick scanner links
bulishurls = [
    "https://chartink.com/screener/double-bottom-1112",
    "https://chartink.com/screener/bullish-momentum-stocks",
    "https://chartink.com/screener/morning-star-candlestick-pattern",
    "https://chartink.com/screener/bullish-engulfing-pattern-1",
    "https://chartink.com/screener/bullish-marubuzo-4",
    "https://chartink.com/screener/piercing-pattern-daily",
    "https://chartink.com/screener/copy-weekly-double-bottom-190",
    "https://chartink.com/screener/hammer-candlestick-pattern",
]
bearishurl=[
    "https://chartink.com/screener/bearish-engulfing-pattern",
    "https://chartink.com/screener/bearish-marubozu-1",
    "https://chartink.com/screener/dark-cloud-cover",
    "https://chartink.com/screener/daily-bullish-harami-2",
    "https://chartink.com/screener/bearish-harami-3",
    "https://chartink.com/screener/evening-star",
]

urls=bulishurls #+bearishurl
# Open each URL in a new browser tab
for url in urls:
    webbrowser.open_new_tab(url)
    time.sleep(1)
