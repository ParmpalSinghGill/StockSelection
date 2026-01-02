import datetime
from ftplib import parse150
from operator import le
import os,json
from re import T
from multiprocessing import Pool

import pandas as pd
import heapq
from itertools import starmap
from collections import defaultdict


BasePath="Scraper/MFStocks/"


def GetLatestFile(fileList,k=1):
    if not fileList:
        return None
    latest_file = sorted(fileList, key=os.path.getmtime,)[::-1]
    # latest_file = heapq.nlargest(k, fileList, key=os.path.getmtime)
    return latest_file

def GetAllMFLatestFiles(BasePath,k=1,newfile=None,oldfile=None):
    LatestFiles=[([os.path.join(BasePath,MF,file) for file in os.listdir(BasePath+MF) if not file.startswith(".~") and os.path.getsize(os.path.join(BasePath,MF,file))>10 and len(file.split("_"))>2],k) for MF in os.listdir(BasePath)]
    LatestFiles=list(filter(lambda x:x is not None ,starmap(GetLatestFile,LatestFiles)))
    # LatestFiles=list(filter(lambda x: ))
    if k==1:
        if newfile is not None:
            MFFiles={file[0].split("/")[-2]:file[0] for file in LatestFiles if newfile in file}
        else:
            MFFiles = {file[0].split("/")[-2]: file[0] for file in LatestFiles}
    else:
        if newfile is not None:
            newfiledate=datetime.datetime.strptime(newfile,"%y_%b_%d")
            LatestFiles=[[f for f in file if newfiledate >=datetime.datetime.strptime(f.split("/")[-1].split(".")[0],"%y_%b_%d")] for file in LatestFiles]
            LatestFiles = list(filter(lambda x: len(x)>0, LatestFiles))
        if oldfile is not None:
            MFFiles = {file[0]: [f for f in file if oldfile in f] for file in LatestFiles}
            MFFiles = {file.split("/")[-2]: [file,flist[0]] for file,flist in MFFiles.items() if len(flist)>0}
        else:
            MFFiles = {file[0].split("/")[-2]: file[:k] for file in LatestFiles if len(file)>=k}
    return MFFiles

def compareTwoFiles(latestMf,oldMf):
    # Set 'scheme' as the index for easier comparison
    latestMf_indexed = latestMf.set_index(['scheme', 'instrument'])
    oldMf_indexed = oldMf.set_index(['scheme', 'instrument'])
    latestMf_indexed["percentage"]=latestMf_indexed["percentage"].map(lambda x:float(str(x).removesuffix("%")))
    oldMf_indexed["percentage"]=oldMf_indexed["percentage"].map(lambda x:float(str(x).removesuffix("%")))
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
                'status': '\033[92mIncreased\033[0m' if new_pct > old_pct else '\033[91mDecreased\033[0m',
                'sector':oldMf_indexed.loc[key, 'sector']
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
            if "old_percentage" in row and "new_percentage" in row:
                print(f"Changed   {row["scheme"]} scheme from {row['old_percentage']}% {row["status"]} to {row["new_percentage"]}% from sector {row['sector']}")
            else:
                print(f"Changed   {row["scheme"]} scheme by {row['percentage']}% from sector {row['sector']}")

def analyze_percentage_changes(pairs_of_dfs):
    """
    Analyze percentage-based additions and deletions of instruments across mutual fund schemes.

    Parameters:
    - pairs_of_dfs: List of (old_df, new_df) tuples. Each DataFrame has:
        ['scheme', 'sector', 'instrument', 'percentage']

    Returns:
    - added_percentages: dict of {instrument: total_percentage_added}
    - removed_percentages: dict of {instrument: total_percentage_removed}
    - net_changes: dict of {instrument: net_percentage_change (positive or negative)}
    """
    added_percentages = defaultdict(float)
    removed_percentages = defaultdict(float)

    for old_file, new_file in pairs_of_dfs:
        # print(old_file,os.path.getsize(old_file),new_file,os.path.getsize(new_file))
        old_df=pd.read_csv(old_file)
        new_df=pd.read_csv(new_file)
        schemes = set(old_df['scheme']).union(new_df['scheme'])

        for scheme in schemes:
            old = old_df[old_df['scheme'] == scheme].set_index('instrument')['percentage']
            new = new_df[new_df['scheme'] == scheme].set_index('instrument')['percentage']

            all_instruments = set(old.index).union(new.index)
            for inst in all_instruments:
                old_pct = old.get(inst, 0)
                new_pct = new.get(inst, 0)
                if isinstance(old_pct,pd.Series): old_pct=old_pct.iloc[-1]
                if isinstance(new_pct,pd.Series): new_pct=new_pct.iloc[-1]
                old_pct,new_pct=str(old_pct).removesuffix("%"),str(new_pct).removesuffix("%")
                old_pct,new_pct=float(old_pct),float(new_pct)
                diff = new_pct - old_pct

                if diff > 0:
                    added_percentages[scheme] += diff
                elif diff < 0:
                    removed_percentages[scheme] += -diff


    # Net change = added - removed
    net_changes = {
        inst: added_percentages.get(inst, 0) - removed_percentages.get(inst, 0)
        for inst in set(added_percentages) | set(removed_percentages)
    }

    return dict(added_percentages), dict(removed_percentages), net_changes

def countAddedRemovedAndChangedStocks(stock,df_pair):
    Added,Removed=[],[]
    TotalStocks=[]
    # print(f"*************************** Stock {stock} ***************************")
    for mfName,mfFiles in df_pair.items():
        if len(mfFiles)!=2: continue
        LatestFile,oldFile=mfFiles
        latestMf=pd.read_csv(LatestFile)
        oldMf=pd.read_csv(oldFile)
        latestMf,oldMf=latestMf[latestMf["scheme"]==stock],oldMf[oldMf["scheme"]==stock]
        latestMf,oldMf=latestMf.reset_index(drop=True),oldMf.reset_index(drop=True)
        if len(latestMf)>0:
            TotalStocks.append({"name":mfName,"Holding Percnetage":latestMf.loc[0,"percentage"]})
        # if len(latestMf)>0 and len(oldMf)>0:
        #     print(f"MFName {mfName}  oldMF have {oldMf.loc[0,"percentage"]} NewMf have {latestMf.loc[0,"percentage"]}")
        # elif len(latestMf)>0 :
        #     print(f"MFName {mfName} NewMf have {latestMf.loc[0,"percentage"]}")
        # elif len(oldMf)>0 :
        #     print(f"MFName {mfName} oldMF have {oldMf.loc[0,"percentage"]}")
                        
        if latestMf.shape[0]==0 and oldMf.shape[0]==0: continue
        new_rows, deleted_rows, percentage_change_df=compareTwoFiles(latestMf,oldMf)
        if new_rows.shape[0]>0:Added.append((mfName,new_rows.loc[0,"percentage"]))
        if deleted_rows.shape[0]>0:
            Removed.append((mfName,deleted_rows.loc[0,"percentage"]))
        if percentage_change_df.shape[0]>0:
            if "Decreased" in percentage_change_df["status"]:
                Removed.append((mfName,-deleted_rows.loc[0,"change"]))
    return Added,Removed,TotalStocks


ResultsDir="Results/"
def getUpdatesInMfsAccordingToStock(ctype="Added",newfile=None,oldfile=None,N=-1,OutFolder="Recomendation/"):
    """
    It Checks How many stocks are Added removed, Increased or decreased in MF
    :return:
    """
    mfFiles=GetAllMFLatestFiles(BasePath,k=2,newfile=newfile,oldfile=oldfile)
    added, removed, net_changes=analyze_percentage_changes(list(mfFiles.values()))
    if ctype=="Removed":
        stocklist=[[k,v] for k,v in removed.items()]
    else:
        stocklist=[[k,v] for k,v in added.items()]
    stocklist=sorted(stocklist,key=lambda x:x[1],reverse=True)
    FullResults,CountResultas={},[]
    TotalStocksDict={}
    for stock,percent in stocklist:
        # print(stock,mfFiles)
        Added,Removed,TotalStocks=countAddedRemovedAndChangedStocks(stock,mfFiles)
        TotalStocksDict[stock]=TotalStocks
        if len(Added)>0 or len(Removed)>0:
            FullResults[stock]={"Added":Added,"Removed":Removed}
            CountResultas.append([stock,len(Added),len(Removed)])
            print(stock,f"Added in {len(Added)} MF and Removed from  {len(Removed)} MFS" )
    os.makedirs(ResultsDir,exist_ok=True)
    with open(f"{ResultsDir}/FullResuts.json","w") as f:
        json.dump(FullResults,f,indent=4)
    with open(f"{ResultsDir}/TotalStocks.json","w") as f:
        json.dump(TotalStocksDict,f,indent=4)
    df=pd.DataFrame(CountResultas,columns=["Stock","AddedCount","RemovedCount"])
    df["BalanceCount"]=df["AddedCount"]-df["RemovedCount"]
    if newfile is not None and oldfile is not None:
        ResultFile = f"{newfile}--{oldfile}"
    elif newfile is not None or oldfile is not None:
        ResultFile = {newfile} if newfile is not None else oldfile
    else:
        ResultFile=f"{datetime.datetime.now().strftime("%y-%m-%d")}"
    df.to_csv(f"{ResultsDir}/Resuts_{ResultFile}.csv",index=None)
    print("Full Results Saved At",f"{ResultsDir}/Resuts.csv")
    os.makedirs(OutFolder,exist_ok=True)
    df=df.sort_values(by="BalanceCount",ascending=False)
    filepath=f"{OutFolder}/Recomendation_{ResultFile}.csv"
    df[:N].to_csv(filepath,index=None)
    print(f"File save at {filepath}")

  


def getMFDicts(BasePath=BasePath,equityOnly=False,toLower=True):
    MFDict={}
    for MFName,file in GetAllMFLatestFiles(BasePath).items():
        df=pd.read_csv(file)
        df["percentage"]=df["percentage"].map(lambda x:float(str(x).removesuffix("%")))
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
    stockName=stockName.lower()
    if "ltd." in stockName and "ltd" not in stockName:
        stockName=stockName.lower().replace("ltd","ltd.")
    stockName=stockName.replace("limited","ltd.")
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
    StockInfo=[]
    for i,row in df.iterrows():
        SName=row["Stock Name"]
        MFLIST=GetMFPerncentageForScock(SName,MFDICT)
        StockInfo.append([len(MFLIST),row,MFLIST])
    # StockInfo.sort(key=lambda x:x[0])
    for mfcount,row,MFLIST in StockInfo:
        PorFoliowPercent = row["Closing value"] / TotalAmount * 100
        SName = row["Stock Name"]
        print("*"*50)
        print(f"{SName} in my PortFolio is {PorFoliowPercent:.2f}% with {row["Closing value"]:.2f} Value")
        if len(MFLIST)>0:
            print(f"Holding {len(MFLIST)} MF")
            # for MFNMAE,DF in MFLIST.items():
            #     for j,rowmf in DF.iterrows():
            #         print(f"           {MFNMAE} have {rowmf["percentage"]}% in {rowmf["instrument"]} from  {rowmf["sector"]} sector")
        else:
            print("                 No Holding in MF")


def getPercentageforEachStock(recomendfile,expandline=5):
    MFDICT = getMFDicts(BasePath=BasePath, equityOnly=True)
    df=pd.read_csv(recomendfile)[:10]
    for i, row in df.iterrows():
        SName = row["Stock"]
        MFLIST = GetMFPerncentageForScock(SName, MFDICT)
        print(f"For Stock {SName} we have {len(MFLIST)} MF")
        i=0
        for mf,df in MFLIST.items():
            i+=1
            print(mf,df)


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

def getAllTheFIleswithMinNdaysDifference(BasePath="MFStocks/Motilal_Oswal_Midcap_Fund_Direct_Growth/",N=5):
    filelist=[]
    AllFiles={file:datetime.datetime.strptime(file.split(".")[0],"%y_%b_%d") for file in os.listdir(BasePath)}
    for file,filetime in AllFiles.items():
        filetime-=datetime.timedelta(days=N)
        oldfiles=[(f,ft) for f,ft in AllFiles.items() if ft<=filetime]
        oldfiles=sorted(oldfiles,key=lambda x:x[1])[::-1]
        if len(oldfiles)>0:
            filelist.append([file,oldfiles[0][0]])
    return filelist



def process_pair(pair):
    newfile, oldfile = pair
    getUpdatesInMfsAccordingToStock(
        newfile=newfile.split(".")[0],
        oldfile=oldfile.split(".")[0]
    )

# CheckPercentageWeHave(BasePath)
# ComparePercnetageForMyShares("TempFiles/Stocks_Holdings_Statement_5364437922_13-10-2025.xlsx")

# CompareStcoksInALLMF(BasePath)
# print(GetMFPerncentageForScock("HDFC BANK LTD",getMFDicts(BasePath=BasePath,equityOnly=True)))
# GetStocksInMostMfs()


if __name__ == '__main__':
    # getUpdatesInMfs()
    # getUpdatesInMfsAccordingToStock(newfile="25_NOV_30",oldfile="25_NOV_01")
    getPercentageforEachStock("Recomendation/Recomendation_25_NOV_30--25_NOV_01.csv")
    # pairs = list(getAllTheFIleswithMinNdaysDifference(N=10))
    #
    # with Pool(16) as p:
    #     p.map(process_pair, pairs)


"""
3000489923
3007622757
"""