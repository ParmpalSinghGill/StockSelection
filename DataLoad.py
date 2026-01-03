import os,time
import difflib
import pickle
import pickle as pk
import pandas as pd

StockDataFolder="/media/parmpal/Data/Codes/MyCodes/StockS/StockBackTesting/StockData/"
# os.makedirs("StockData/INDEX", exist_ok=True)

AllStocks=None
ComditiyDict=None

tickerMapping = {
    "NIFTY50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    2: "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
    3: "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    4: "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
    5: "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    6: "https://archives.nseindia.com/content/indices/ind_niftysmallcap50list.csv",
    7: "https://archives.nseindia.com/content/indices/ind_niftysmallcap100list.csv",
    8: "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    9: "https://archives.nseindia.com/content/indices/ind_niftymidcap50list.csv",
    10: "https://archives.nseindia.com/content/indices/ind_niftymidcap100list.csv",
    11: "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    14: "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
}

os.makedirs("Results", exist_ok=True)
def getDatFrame(stockData):
    try:
        return pd.DataFrame(stockData["data"],columns=stockData["columns"],index=stockData["index"])
    except Exception as e:
        print(stockData)
        raise e

def readFile(path):
    try:
        with open(path, "rb") as f:
            return  pk.load(f)
    except FileNotFoundError:
        with open("../"+path, "rb") as f:
            return  pk.load(f)
            

def getTickerFromName(name):
    global ComditiyDict
    if ComditiyDict is None:
        ComditiyDF=pd.read_csv(StockDataFolder+"EQUITY_L.csv")
        ComditiyDict={row["NAME OF COMPANY"].lower():row["SYMBOL"] for i,row in ComditiyDF.iterrows()}
    if name in ComditiyDict.values():
        return name
    name=name.lower().replace("ltd","limited")
    expcase={"adani port & sez limited":"ADANIPORTS"}
    if name in expcase:
        return expcase[name]
    matches = difflib.get_close_matches(name, ComditiyDict.keys(), n=1, cutoff=0.6)
    if matches:
        return ComditiyDict[matches[0]]
    return None

def getStockNameFromSymbol(symbol):
    ComditiyDict=pd.read_csv(StockDataFolder+"EQUITY_L.csv")
    return ComditiyDict[ComditiyDict["SYMBOL"]==symbol]["NAME OF COMPANY"].values[0]

import threading

_data_lock = threading.Lock()

def getData(key=None):
    global AllStocks,ComditiyDict
    
    if AllStocks is None:
        with _data_lock:
            if AllStocks is None: # Double-check locking pattern
                AllStocks=readFile(StockDataFolder+"AllSTOCKS.pk")
                
    if key is None:
        return AllStocks
    elif key in AllStocks:
        return getDatFrame(AllStocks[key])
    elif key in ['NIFTY50', 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14]:
        IndexPath=f"{StockDataFolder}INDEX/{key}.pk"
        if not os.path.exists(IndexPath) or (time.time() - os.path.getmtime(IndexPath)) > 2629800: # ~30.4 days
            symbollist=pd.read_csv(tickerMapping[key])["Symbol"].values
            with open(IndexPath,"wb") as f:
                pickle.dump(symbollist,f)
        with open(IndexPath,"rb") as f:
            symbollist=pickle.load(f)
        return {k:v for k,v in AllStocks.items() if k in symbollist}
    else:
        if ComditiyDict is None:
            ComditiyDict=pd.read_csv(StockDataFolder+"EQUITY_L.csv")
            ComditiyDict={row["NAME OF COMPANY"].lower():row["SYMBOL"] for i,row in ComditiyDict.iterrows()}
        if key.lower() in ComditiyDict:
            return getDatFrame(AllStocks[ComditiyDict[key.lower()]])            
        else:
            ticker = getTickerFromName(key)
            if ticker:
                # print(f"Ticker found for {key} : {ticker}")
                if ticker in AllStocks:
                    return getDatFrame(AllStocks[ticker])
            # print(f"Key {key} not found")
            return None




# def getMyStocks():
#     with open("DataProcessing/MyStock") as f:
#         data=[d[:-1] for d in f.readlines()]
#     return data


