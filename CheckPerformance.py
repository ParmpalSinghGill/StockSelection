import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pickle as pk

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

AllStocks="/media/parmpal/Data/Codes/MyCodes/StockS/StockBackTesting/StockData/AllSTOCKS.pk"
NiftyDf=pd.read_csv("/media/parmpal/Data/Codes/MyCodes/StockS/StockBackTesting/StockData/INDEXData/Comudities.csv")
NiftyDf.index=pd.to_datetime(NiftyDf["Date"])

NiftyDf=NiftyDf[[c for c in NiftyDf.columns if "NIFTY50" in c]]
NiftyDf=NiftyDf.rename(columns={c:c.replace("NIFTY50_","") for c in NiftyDf.columns})





with open(AllStocks,"rb") as f:
    stock_data=pk.load(f)

stocknames=pd.read_csv("/media/parmpal/Data/Codes/MyCodes/StockS/StockBackTesting/Stocks/EQUITY_L.csv")
stocknames={row["NAME OF COMPANY"].lower():row["SYMBOL"] for i,row in stocknames.iterrows()}

def getWorkingDf(df,strategy="Greedy",diff=0.5):
    if strategy=="Exact_with_benifts":
        buyprice=df.at[df.index[0],"Close"]*(1-diff/100)
        selprice=df.at[df.index[-1],"Close"]
        workingdf=df
    elif strategy=="Greedy":
        buyprice=df.at[df.index[0],"Close"]*(1+diff/100)
        selprice=df.at[df.index[-1],"Close"]
        workingdf=df
    elif strategy=="Green":
        # buy at next green candle
        selprice=df.at[df.index[-1],"Close"]
        greendf=df[df["Close"]>df["Open"]]
        workingdf=df[df.index>=greendf.index[0]]
        if workingdf.shape[0]>0:
            buyprice=workingdf.at[workingdf.index[0],"Close"]*(1+diff/100)
        else:
            buyprice=selprice
    else:
        raise Exception(f"{strategy} Startegy not supported")
    return workingdf,buyprice,selprice

def checkPerformance(sname,df,strategy="Greedy",diff=0.5,detailed=False):
    workingdf, buyprice, selprice=getWorkingDf(df,strategy=strategy,diff=diff)
    if buyprice > selprice:
        change = (buyprice - selprice) * 100 / buyprice
        if detailed:
            print(f"{RED}{sname:40s} price ↓ {change:.2f}% from {buyprice:7.2f} to {selprice:7.2f}{RESET}")
    else:
        change = (selprice - buyprice) * 100 / buyprice
        if detailed:
            print(f"{GREEN}{sname:40s} price ↑ {change:.2f}% from {buyprice:7.2f} to {selprice:7.2f}{RESET}")
    return (selprice - buyprice) * 100 / buyprice

def getStockData(sname,startdate):
    try:
        sname = sname.lower().removesuffix(".").replace("ltd", "limited").replace("and", "&")
        if sname not in stocknames:
            return None,None
        sd = stock_data[stocknames[sname]]
        sdf = pd.DataFrame(sd["data"], columns=sd["columns"], index=pd.to_datetime(sd["index"]))
        sdf = sdf.loc[sdf.index >= startdate]
        return sdf,sdf.index[-1]
    except:
        # print(f"Expcetion in Collecting stock data for {sname} not in {stock_data.keys()}")
        return None,None

def SimplePerformace(RecomendFile,strategy="Greedy",MinimumAdd=1,detailed=False):
    if len(RecomendFile)<45:
        startdate = pd.to_datetime(RecomendFile.split("/")[-1].split("_")[-1].split(".")[0], format="%y-%m-%d")
    else:
        startdate = pd.to_datetime(RecomendFile.split("/")[-1].split("--")[-1].split(".")[0], format="%y_%b_%d")
    startdate+=datetime.timedelta(days=1)
    recomenddf = pd.read_csv(RecomendFile)
    recomenddf=recomenddf[recomenddf["AddedCount"]>=MinimumAdd]
    if len(recomenddf)==0:
        print(f"No Stock in {RecomendFile}")
        return
    i=0
    while True:
        try:
            sdata,lastdate=getStockData(recomenddf.values[i,0],startdate)
        except:pass
        i+=1
        if i>recomenddf.shape[0]:break
        if sdata is not None:break
    if sdata is None:
        print(f"No Stock in {RecomendFile}")
        return
    nifty_return=checkPerformance("Nifty",NiftyDf.loc[NiftyDf.index >= startdate],strategy="Exact_with_benifts")
    if detailed:
        print(f"Performance after {(lastdate-startdate).days} All Days and {sdata.shape[0]} Working days")
    returns=[]
    for i,row in recomenddf.iterrows():
        sdf,_=getStockData(row["Stock"],startdate)
        if sdf is None:
            # print(f"{row['Stock']} not found so skipping" )
            continue
        returns.append(checkPerformance(row["Stock"],sdf,strategy=strategy,detailed=detailed))
    print(f"{RecomendFile.split("/")[-1]} Overall give {np.mean(returns):.2}% Returns in {sdata.shape[0]} working days and {(lastdate-startdate).days} All days where nifty do {nifty_return}")

def PlotAllStocksPerformance(StockData:dict,plotType=["Indvidial","Combined","Overall"]):
    # niftydf["PL"]=niftydf["Close"]-niftybyprice
    # niftydf["PL%"]=(niftydf["PL"]/niftybyprice)*100
    for sname,(bprice,df) in StockData.items():
        df.loc[df.index,"PL"]=df["Close"]-bprice
        df.loc[df.index,"PL%"]=(df["PL"]/bprice)*100
    niftybyprice,niftydf=StockData["Nifty"]
    AllCLose=niftydf.copy()[["PL%"]].rename(columns={"PL%":"Nifty"})
    for sname,(bprice,df) in StockData.items():
        if sname=="Nifty": continue
        if "Indvidial" in plotType:
            plt.figure(figsize=(20, 12))
            plt.plot(niftydf.index,niftydf["PL%"],label="Nifty")
            plt.plot(df.index,df["PL%"],label=sname)
            plt.legend()
            plt.title(f"{sname} gain {df.loc[df.index[-1],'PL%']:.2f}% nifty gained {niftydf.loc[df.index[-1],'PL%']:.2f}% ")
            plt.show()
        AllCLose[sname]=df["PL%"]
    AllCLose=AllCLose.ffill().bfill()
    if "Combined" in plotType:
        plt.Figure(figsize=(20, 12))
        for col in AllCLose.columns:
            plt.plot(AllCLose.index,AllCLose[col],label=f"{col} ({AllCLose.loc[AllCLose.index[-1],col]:.2f}%)")
        plt.legend()
        plt.title(f"All Stocks")
        plt.show()
    AllCLose["Overall"]=AllCLose[list(filter(lambda x: x!="Nifty",AllCLose.columns))].mean(axis=1)
    if "Overall" in plotType:
        plt.Figure(figsize=(20, 12))
        for col in ["Nifty","Overall"]:
            plt.plot(AllCLose.index, AllCLose[col], label=f"{col} ({AllCLose.loc[AllCLose.index[-1], col]:.2f}%)")
        plt.legend()
        plt.title(f"All Stocks")
        plt.show()
    return AllCLose.loc[AllCLose.index[-1],"Overall"],AllCLose.loc[AllCLose.index[-1],"Nifty"]



def detailedPerformace(RecomendFile,strategy="Greedy",diff=0.5,MinimumAdd=1):
    if len(RecomendFile)<45:
        startdate = pd.to_datetime(RecomendFile.split("/")[-1].split("_")[-1].split(".")[0], format="%y-%m-%d")
    else:
        startdate = pd.to_datetime(RecomendFile.split("/")[-1].split("--")[-1].split(".")[0], format="%y_%b_%d")
    startdate+=datetime.timedelta(days=1)
    recomenddf = pd.read_csv(RecomendFile)
    recomenddf=recomenddf[recomenddf["AddedCount"]>=MinimumAdd]
    sdata,lastdate=getStockData(recomenddf.values[0,0],startdate)
    niftydf, niftybuyprice, _ = getWorkingDf(NiftyDf.loc[NiftyDf.index >= startdate], strategy="Exact_with_benifts", diff=diff)
    print(f"Performance after {(lastdate-startdate).days} All Days and {sdata.shape[0]} Working days")
    StockData= {"Nifty":(niftybuyprice,niftydf)}
    for i,row in recomenddf.iterrows():
        sdf,_=getStockData(row["Stock"],startdate)
        if sdf is None:
            print(f"{row['Stock']} not found so skipping" )
            continue
        sworkingdf, sbuyprice, _ = getWorkingDf(sdf, strategy=strategy, diff=diff)
        StockData[row["Stock"]]=(sbuyprice,sworkingdf)
        # returns.append(checkPerformance(row["Stock"],sdf,strategy=strategy))
    overallreturns,nifty_return=PlotAllStocksPerformance(StockData,plotType=["Overall"])
    print(f"Overall give {overallreturns}% Returns in {sdata.shape[0]} working days and {(lastdate-startdate).days} All days where nifty do {nifty_return}")

def getPerformanceForLatsetN(BasePath,N=11,strategy="Greedy",MinimumAdd=1):
    files=sorted(list(filter(lambda x:x.startswith("Recomendation"),os.listdir(BasePath))),key=lambda x: os.path.getmtime(BasePath+x))[::-1][:N]
    for file in files:
        SimplePerformace(BasePath+file, strategy=strategy,MinimumAdd=MinimumAdd)

strategy="Greedy" #Greedy, Green
# RecomendFile="Recomendation/Recomendation_25-09-14.csv"
RecomendFile="Recomendation/Recomendation_25-10-06.csv"
# RecomendFile="Recomendation/Recomendation_25-11-01.csv"
# RecomendFile="Recomendation/Recomendation_25_OCT_07--25-10-14.csv"
# RecomendFile="Recomendation/Recomendation_25_SEP_14--25-10-07.csv"
# RecomendFile="Recomendation/Recomendation_25_AUG_20--25_JUL_06.csv"
# RecomendFile="Recomendation/Recomendation_25_NOV_20--25_NOV_01.csv"
# RecomendFile="Recomendation/Recomendation_25_NOV_01--25_OCT_19.csv"
SimplePerformace(RecomendFile,strategy="Greedy",detailed=True)
# detailedPerformace(RecomendFile,strategy="Green",MinimumAdd=3)

# getPerformanceForLatsetN(BasePath="Recomendation/",N=11,strategy="Greedy",MinimumAdd=3)
