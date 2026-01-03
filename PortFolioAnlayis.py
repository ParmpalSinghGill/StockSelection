from collections import defaultdict
import pandas as pd
from DataLoad import getData,getStockNameFromSymbol,getTickerFromName
from PlotingCode.PlotCandles import PlotChart 
from SupportANDResistentChannel import SRChannels   # adjust import if needed


# ---------------------------------------------------------
# Helpers to interpret SRChannels output
# SR format: [zone_high, zone_low, strength]
# ---------------------------------------------------------

def split_sr_zones(sr_zones, current_price):
    supports = []
    resistances = []

    for high, low, strength in sr_zones:
        zone_high = max(high, low)
        zone_low = min(high, low)

        zone = {
            "high": zone_high,
            "low": zone_low,
            "strength": strength
        }

        if zone_high < current_price:
            supports.append(zone)
        elif zone_low > current_price:
            resistances.append(zone)

    # nearest first
    supports = sorted(supports, key=lambda z: abs(current_price - z["high"]))
    resistances = sorted(resistances, key=lambda z: abs(z["low"] - current_price))

    return supports, resistances


def support_break(df, zone, confirm=2):
    closes = df["Close"].iloc[-confirm:]
    return all(closes < zone["low"])


def resistance_break(df, zone, confirm=2):
    closes = df["Close"].iloc[-confirm:]
    return all(closes > zone["high"])


def support_reject(df, zone):
    last = df.iloc[-1]
    return last["Low"] <= zone["low"] and last["Close"] > zone["high"]


def resistance_reject(df, zone):
    last = df.iloc[-1]
    return last["High"] >= zone["high"] and last["Close"] < zone["low"]


# ---------------------------------------------------------
# MAIN NARRATIVE FUNCTION (REPLACES price_level_story)
# ---------------------------------------------------------

def price_level_story(df, sr_zones):
    """
    df:
      - DateTimeIndex
      - OHLC columns
    sr_zones:
      - output of SRChannels.getSupportAndRessitent()
    returns:
      - human-readable analysis string
    """

    df = df.sort_index()
    price = df["Close"].iloc[-1]

    story = []

    supports, resistances = split_sr_zones(sr_zones, price)

    # ---------------- SUPPORT ANALYSIS ----------------
    if supports:
        s = supports[0]

        if support_break(df, s):
            story.append(
                f"Price closed below a strong support zone "
                f"({s['low']:.1f}–{s['high']:.1f}, strength {s['strength']}), "
                f"indicating structural weakness."
            )
        elif support_reject(df, s):
            story.append(
                f"Price rejected the support zone "
                f"({s['low']:.1f}–{s['high']:.1f}), "
                f"suggesting buyers are defending this level."
            )
        else:
            dist = (price - s["high"]) / s["high"] * 100
            story.append(
                f"Nearest support lies at "
                f"{s['low']:.1f}–{s['high']:.1f} "
                f"({dist:.1f}% away)."
            )

    # ---------------- RESISTANCE ANALYSIS ----------------
    if resistances:
        r = resistances[0]

        if resistance_break(df, r):
            story.append(
                f"Price closed above a key resistance zone "
                f"({r['low']:.1f}–{r['high']:.1f}, strength {r['strength']}), "
                f"indicating a potential breakout."
            )
        elif resistance_reject(df, r):
            story.append(
                f"Price tested resistance at "
                f"{r['low']:.1f}–{r['high']:.1f} "
                f"but failed to close above it."
            )
        else:
            dist = (r["low"] - price) / r["low"] * 100
            story.append(
                f"Nearest resistance lies at "
                f"{r['low']:.1f}–{r['high']:.1f} "
                f"({dist:.1f}% away)."
            )

    if not story:
        story.append(
            "Price is trading between support and resistance zones "
            "with no structural change."
        )

    # ---------------- TIMEFRAME STATS ----------------
    periods = [
        ("1M", 30),
        ("3M", 90),
        ("6M", 180),
        ("1Y", 365),
        ("3Y", 1095),
        ("5Y", 1825)
    ]
    
    stats = []
    last_date = df.index[-1]
    
    for label, days in periods:
        start_date = last_date - pd.Timedelta(days=days)
        sub_df = df[df.index >= start_date]
        if not sub_df.empty:
            h = sub_df["High"].max()
            l = sub_df["Low"].min()
            dh = (h- price) / h * 100
            dl = (price - l) / l * 100
            stats.append(f"({label}: {dh:.1f}%H/{dl:.1f}%L)")

    # All Time
    ath = df["High"].max()
    atl = df["Low"].min()
    d_ath = (ath-price) / ath * 100
    d_atl = (price - atl) / atl * 100
    stats.append(f"(All Time: {d_ath:.1f}%H/{d_atl:.1f}%L)")
    
    story.append("\nDiffs: [" + " | ".join(stats) + "]")

    return " ".join(story)


# ---------------------------------------------------------
# PORTFOLIO DATA LOADER (UNCHANGED)
# ---------------------------------------------------------

def AllPortfolioStocksData():
    df = pd.read_excel(
        "PortFolio/Stocks_Holdings_Statement_5364437922_30-12-2025.xlsx",
        skiprows=10
    )
    df=df[~df["Stock Name"].str.contains("ETF")]
    df["Ticker"]=df["Stock Name"].map(getTickerFromName)
    df.dropna(subset=["Ticker"], inplace=True)

    pfDict = {}

    for sn in df["Ticker"].values:
        data = getData(sn)
        if data is None:
            print(f"Key {sn} not found")
        else:
            pfDict[sn] = data

    df2 = pd.read_csv("PortFolio/holdings.csv")
    for sn in df2["Instrument"].values:
        data = getData(sn)
        if data is None:
            print(f"Key {sn} not found")
        else:
            pfDict[sn] = data
    holdingdict=defaultdict(tuple)
    for sn in pfDict.keys():
        if sn in df["Ticker"].values and sn in df2["Instrument"].values:
            subdf1=df.loc[df["Ticker"] == sn]
            subdf2=df2.loc[df2["Instrument"] == sn]
            totalquantity=subdf1["Quantity"].values[0]+subdf2["Qty."].values[0]
            averagebuyprice=(subdf1["Average buy price"].values[0]*subdf1["Quantity"].values[0]+subdf2["Avg. cost"].values[0]*subdf2["Qty."].values[0])/(subdf1["Quantity"].values[0]+subdf2["Qty."].values[0])
            holdingdict[sn]=(totalquantity,averagebuyprice)
        elif sn in df["Ticker"].values:
            subdf1=df.loc[df["Ticker"] == sn]
            totalquantity=subdf1["Quantity"].values[0]
            averagebuyprice=subdf1["Average buy price"].values[0]
            holdingdict[sn]=(totalquantity,averagebuyprice)
        elif sn in df2["Instrument"].values:
            subdf2=df2.loc[df2["Instrument"] == sn]
            totalquantity=subdf2["Qty."].values[0]
            averagebuyprice=subdf2["Avg. cost"].values[0]
            holdingdict[sn]=(totalquantity,averagebuyprice)
    
    pfDict={getStockNameFromSymbol(k):v for k,v in pfDict.items()}
    holdingdict={getStockNameFromSymbol(k):v for k,v in holdingdict.items()}

    # df["Tickerame"]

    return pfDict,holdingdict


# ---------------------------------------------------------
# MAIN ANALYSIS LOOP
# ---------------------------------------------------------

def Analysis():
    timeframe = "1D"
    prd = 10
    loopback = 365
    channel_width_pct = 6
    min_strength = 1
    max_num_sr = 6

    for sname, df in AllPortfolioStocksData()[0].items():
        # try:
            sr = SRChannels(
                period=prd,
                channel_width_percentage=channel_width_pct,
                min_strength=min_strength,
                max_num_sr=max_num_sr,
                loopback=loopback,
                SRSelection="Nearest",
                addstrengh=True
            )

            sr_zones = sr.getSupportAndRessitent(df)
            story=price_level_story(df, sr_zones)
            print("*" * 150)
            print(sname)
            print(story)
            PlotChart(df[-365:],Trend=f"{sname} ({df.iloc[-1]['Close']:.2f})\n{story}",Bars=sr_zones)

        # except Exception as e:
        #     print("*" * 150)
        #     print(sname, "ERROR:", e)


if __name__ == "__main__":
    # Analysis()
    print(AllPortfolioStocksData()[0].keys())
