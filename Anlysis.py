import os,json

import pandas as pd
import heapq
from itertools import starmap
from collections import defaultdict


BasePath="MFStocks/"


def GetLatestFile(fileList,k=1):
    if not fileList:
        return None
    # latest_file = sorted(fileList, key=os.path.getmtime,)[::-1][:k]
    latest_file = heapq.nlargest(k, fileList, key=os.path.getmtime)
    return latest_file

def GetAllMFLatestFiles(BasePath,k=1):
    LatestFiles=[([os.path.join(BasePath,MF,file) for file in os.listdir(BasePath+MF) if not file.startswith(".~")],k) for MF in os.listdir(BasePath)]
    LatestFiles=list(starmap(GetLatestFile,LatestFiles))
    if k==1:
        MFFiles={file[0].split("/")[1]:file[0] for file in LatestFiles}
    else:
        MFFiles = {file[0].split("/")[1]: file[:k] for file in LatestFiles}
    return MFFiles

def compareTwoFiles(latestMf,oldMf):
    # Set 'scheme' as the index for easier comparison
    latestMf_indexed = latestMf.set_index(['scheme', 'instrument'])
    oldMf_indexed = oldMf.set_index(['scheme', 'instrument'])
    latestMf_indexed["percentage"]=latestMf_indexed["percentage"].map(lambda x:float(x.removesuffix("%")))
    oldMf_indexed["percentage"]=oldMf_indexed["percentage"].map(lambda x:float(x.removesuffix("%")))
    oldMf_indexed = oldMf_indexed[~oldMf_indexed.index.duplicated(keep='last')]
    latestMf_indexed = latestMf_indexed[~latestMf_indexed.index.duplicated(keep='last')]
    # Set composite key as index

    # New rows (present in latest, not in old)
    new_rows = latestMf_indexed.loc[~latestMf_indexed.index.isin(oldMf_indexed.index)].reset_index()

    # Deleted rows (present in old, not in latest)
    deleted_rows = oldMf_indexed.loc[~oldMf_indexed.index.isin(latestMf_indexed.index)].reset_index()


    # Common keys
    common_keys = latestMf_indexed.index.intersection(oldMf_indexed.index)

    # Compare percentages for common keys
    percentage_change = []
    for key in common_keys:
        old_pct = oldMf_indexed.loc[key, 'percentage']
        new_pct = latestMf_indexed.loc[key, 'percentage']
        if old_pct != new_pct:
            percentage_change.append({
                'scheme': key[0],
                'instrument': key[1],
                'old_percentage': old_pct,
                'new_percentage': new_pct,
                'change': new_pct - old_pct,
                'status': 'Increased' if new_pct > old_pct else 'Decreased'
            })

    percentage_change_df = pd.DataFrame(percentage_change)
    return new_rows,deleted_rows,percentage_change_df

def getUpdatesInMfs():
    """
    It Check How many stocks are Added removed, Increased or decreased in MF
    :return:
    """
    mfFiles=GetAllMFLatestFiles(BasePath,k=2)
    # mfFiles={k:v for k,v in mfFiles.items() if k=="HDFC_Balanced_Advantage_Fund_Direct_Growth"}
    for mfName,mfFiles in mfFiles.items():
        if len(mfFiles)!=2: continue
        LatestFile,oldFile=mfFiles
        latestMf=pd.read_csv(LatestFile)
        oldMf=pd.read_csv(oldFile)
        new_rows, deleted_rows, percentage_change_df=compareTwoFiles(latestMf,oldMf)
        if new_rows.shape[0]>0 or deleted_rows.shape[0]>0 or percentage_change_df.shape[0]>0:
            print("**************************",mfName,"*********************************")
        # else:
        #     print("No change in ",mfName,"*******")

        for i,row in new_rows.iterrows():
            print(f"New Added {row["scheme"]} scheme by {row['percentage']}% from sector {row['sector']}")
        for i,row in deleted_rows.iterrows():
            print(f"Deleted   {row["scheme"]} scheme by {row['percentage']}% from sector {row['sector']}")
        for i,row in percentage_change_df.iterrows():
            print(f"Changed   {row["scheme"]} scheme by {row['percentage']}% from sector {row['sector']}")

        # print("\nDeleted Rows (Removed Schemes):")
        # print(deleted_rows)
        #
        # print("\nPercentage Changes in Common Schemes:")
        # print(percentage_change_df)
        #
        # print(olfMf.columns)
        # exit()


def getMFDicts(BasePath=BasePath,equityOnly=False,toLower=True):
    MFDict={}
    for MFName,file in GetAllMFLatestFiles(BasePath).items():
        df=pd.read_csv(file)
        df["percentage"]=df["percentage"].map(lambda x:float(x.removesuffix("%")))
        if equityOnly:
            df=df[df["instrument"]=="Equity"]
        if toLower:
            df["scheme"]=df["scheme"].str.lower()
        if df.shape[0]>0:
            MFDict[MFName]=df
    return MFDict


def CheckPercentageWeHave(BasePath):
    PercentageDict={}
    for MFName,df in getMFDicts(BasePath=BasePath,equityOnly=True):
        df=df[df["instrument"]=="Equity"]
        print(MFName,df["percentage"].sum())
        PercentageDict[PercentageDict]


def GetMFPerncentageForScock(stockName,MFDict):
    stockName=stockName.lower().replace("ltd","ltd.").replace("limited","ltd.").lower()
    MFLIST={}
    for MFNAME,df in MFDict.items():
        df=df[df["scheme"]==stockName]
        if len(df)>0:
            MFLIST[MFNAME]=df
    # if len(MFLIST)==0:
    #     for MFNAME,df in MFDict.items():
    #         print(stockName,"not in ",df["scheme"].values)
    return MFLIST



def ComparePercnetageForMyShares(MyPortFolio):
    MFDICT=getMFDicts(BasePath=BasePath,equityOnly=True)
    df=pd.read_excel(MyPortFolio,skiprows=10)
    TotalAmount=df["Closing value"].sum()
    print("Total Amount",TotalAmount)
    for i,row in df.iterrows():
        PorFoliowPercent=row["Closing value"]/TotalAmount*100
        SName=row["Stock Name"]
        MFLIST=GetMFPerncentageForScock(SName,MFDICT)
        print("*"*50)
        print(f"{SName} in my PortFolio is {PorFoliowPercent:.2f}% with {row["Closing value"]:.2f} Value")
        if len(MFLIST)>0:
            for MFNMAE,DF in MFLIST.items():
                for j,rowmf in DF.iterrows():
                    print(f"           {MFNMAE} have {rowmf["percentage"]}% in {rowmf["instrument"]} from  {rowmf["sector"]} sector")
        else:
            print("                 No Holding in MF")


def CompareStcoksInALLMF(BasePath,MinMFTOShow=2):
    MFDict=getMFDicts(BasePath=BasePath,equityOnly=True)
    UniqueStocksName=list(set(sum([list(df["scheme"].dropna().values) for _,df in MFDict.items()],[])))
    # print(UniqueStocksName)
    UniqueStocksName=sorted(UniqueStocksName)
    for s in UniqueStocksName:
        MFLIST=GetMFPerncentageForScock(s,MFDict)
        if len(MFLIST)>=MinMFTOShow:
            print("*"*20,s,"*"*20)
            for MFNMAE,DF in MFLIST.items():
                for j,rowmf in DF.iterrows():
                    print(f"           {MFNMAE} have {rowmf["percentage"]} in {rowmf["instrument"]} from  {rowmf["sector"]}")

        # print
        # print(s)

def GetStocksInMostMfs():
    MFDICT = getMFDicts(BasePath=BasePath, equityOnly=True)
    AllSchemes=list(set(sum([list(v["scheme"].values) for k,v in MFDICT.items()],[])))
    StockMfDict=defaultdict(list)
    for scheme in AllSchemes:
        for MfName,stockdf in MFDICT.items():
            if sum(scheme==stockdf["scheme"])>0:
                StockMfDict[scheme].append(MfName)
    sorted_keys = sorted(StockMfDict, key=lambda k: len(StockMfDict[k]))[::-1]
    for k in sorted_keys:
        print(k,len(StockMfDict[k]),StockMfDict[k])



# CheckPercentageWeHave(BasePath)
# ComparePercnetageForMyShares("TempFiles/Stocks_Holdings_Statement_5364437922_14-06-2025.xlsx")
# CompareStcoksInALLMF(BasePath)
# print(GetMFPerncentageForScock("HDFC BANK LTD",getMFDicts(BasePath=BasePath,equityOnly=True)))
getUpdatesInMfs()
# GetStocksInMostMfs()

