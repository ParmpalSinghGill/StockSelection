import os,sys,datetime
import numpy as np
import pandas as pd
sys.path.append(".")
from PlotingCode.PlotCandles import PlotChart

# os.chdir("../")
from DataLoad import getData


class SRChannels:
    """
    THis class implement support and resistent channel same for the Trainding view App provides
    """
    def __init__(self, period=10, source='High/Low', channel_width_percentage=6, min_strength=1, max_num_sr=6, loopback=290,SRSelection="Default",addstrengh=False):
        self.period = period
        self.source = source
        self.channel_width_percentage = channel_width_percentage
        self.min_strength = min_strength
        self.max_num_sr = max_num_sr
        self.loopback = loopback-1
        self.calculationDays=600
        self.SRSelection=SRSelection
        self.addstrengh=addstrengh


    def ForwarFillPivots(self, pivot_high, pivot_low):
        pivot_high,pivot_low=pivot_high.iloc[:-self.period+1],pivot_low.iloc[:-self.period+1]
        pivot = pivot_high.where(pivot_high != 0, pivot_low)
        pivot=pivot.reset_index(drop=True)
        pivot=pivot[pivot>0]
        if pivot.shape[0]==0:
            return []
        pivotebeforlopback=pivot[pivot.index > (pivot.index[-1] - self.loopback)].values[::-1]
        seen = set()
        return [x for x in pivotebeforlopback if not (x in seen or seen.add(x))] # remove dupli

    def calculate_pivot_points(self, high, low, close, open_):
        src1 = high if self.source == 'High/Low' else np.maximum(close, open_)
        src2 = low if self.source == 'High/Low' else np.minimum(close, open_)
        pivot_high = (src1 == src1.rolling(self.period * 2 + 1, center=True).max()).astype(float)
        pivot_low = (src2 == src2.rolling(self.period * 2 + 1, center=True).min()).astype(float)
        pivot_high = src1 * pivot_high
        pivot_low = src2 * pivot_low
        return self.ForwarFillPivots(pivot_high, pivot_low)

    def get_SR_vals(self, lo, pivot_vals):
        hi = lo
        num_pp = 0
        for cpp in pivot_vals:
            width = abs(hi - cpp) if cpp <= hi else abs(cpp - lo)
            if width <= self.channel_width:
                lo = min(lo, cpp)
                hi = max(hi, cpp)
                num_pp += self.period*2
        for y in range(self.loopback):
            row=self.df.iloc[-y-1]
            if (row["High"] <= hi and row["High"] >= lo) or (row["Low"] <= hi and row["Low"] >= lo):
                num_pp += 1
        return [num_pp,hi, lo]

    def changeit(self,x, y, suportresistance):
        # Get and swap  pair of elements
        tmp = suportresistance[y]
        suportresistance[y] = suportresistance[x]
        suportresistance[x] = tmp


    def getStrongSupportAndRessitent(self,pivotvals,supres):
        supportandRessitent,stren=[],[]
        src = 0
        for x in range(len(pivotvals)):
            stv=-1
            stl=-1
            for y,sup in enumerate(supres): 
                if sup[0]>stv and sup[0]>=self.min_strength*self.period*2:
                    stv,stl=sup[0],y
            if stl >= 0:
                # get sr level
                hh = supres[stl][1]
                ll = supres[stl][2]
                if self.addstrengh:
                    supportandRessitent.append([hh,ll,supres[stl][0]//self.period*2])
                else:
                    supportandRessitent.append([hh,ll])
                stren.append(supres[stl][0])

                for sp in supres:
                    if sp[1]<=hh and sp[1]>=ll or sp[2]<=hh and sp[2]>=ll:
                        sp[0]=-1
                src += 1
                if src >= 10:break

        for x in range(len(stren)-1):
            for y in range(x+1,len(stren)):
                if stren[y] > stren[x]:
                    stren[y]=stren[x]
                    self.changeit(x,y,supportandRessitent)
        return supportandRessitent

    def getSupportAndRessitent(self,fulldf):
        self.loopback=min(self.loopback,fulldf.shape[0])
        self.df=fulldf
        self.df=self.df[-self.calculationDays:]
        # get Channel width with high low of last year
        self.channel_width=(self.df.iloc[-300:, self.df.columns.get_loc("High")].max() - self.df.iloc[-300:, self.df.columns.get_loc("Low")].min()) * self.channel_width_percentage / 100
        # Calculate Pivot Points
        pivotvals = self.calculate_pivot_points(self.df["High"], self.df["Low"], self.df["Close"], self.df["Open"])
        # print(pivotvals)
        sandr=[self.get_SR_vals(x, pivotvals) for x in pivotvals]
        supres=self.getStrongSupportAndRessitent(pivotvals,sandr)
        # print(len(supres),supres)
        if self.SRSelection=="EqualBoth":
            support=sorted([s for s in supres if s[1]<self.df.iloc[-1, self.df.columns.get_loc("Close")]])
            resistence=sorted([s for s in supres if s[0]>self.df.iloc[-1, self.df.columns.get_loc("Close")]])
            atpoint=[s for s in supres if s[1]>=self.df.iloc[-1, self.df.columns.get_loc("Close")]>=s[0]]
            supres=atpoint
            for s,r in zip(support,resistence):
                supres.append(s)
                supres.append(r)
        elif self.SRSelection=="Nearest":
            # print([(s[0],s[1],) for s in supres])
            supres=sorted(supres,key=lambda x:abs(self.df.iloc[-1, self.df.columns.get_loc("Close")]-(x[0]+x[1])/2))
        supres=supres[:self.max_num_sr]
        return supres


def plotSupportAndRessitent(ticker:str,timeframe:str='1D',prd:int=10,loopback:int=290,channel_width_pct:int=6,min_strength:int=1,max_num_sr:int=6):
    df = getData(ticker)
    if timeframe == '1D':
        pass
    else:
        print("TimeFrame not supported")
        return
    sr = SRChannels(period=prd,channel_width_percentage=channel_width_pct,min_strength=min_strength,max_num_sr=max_num_sr,loopback=loopback,SRSelection="Nearest",addstrengh=True)
    spandr=sr.getSupportAndRessitent(df)
    print(spandr)
    PlotChart(df[-150:],Trend=f"S&R for {ticker}",Bars=spandr)

# Example Usage
def main(ticker):
    # # Input Parameters
    # timeframe = '1D'  # Higher Time Frame
    # prd = 10  # Pivot Period
    # loopback = 290  # 290  # Loopback Period
    # channel_width_pct = 6  # Maximum Channel Width (%)
    # min_strength = 1  # Minimum Strength
    # max_num_sr = 6  # Maximum Number of S/R to Show

    timeframe = '1D'  # Higher Time Frame
    prd = 10  # Pivot Period
    loopback = 365  # 290  # Loopback Period
    channel_width_pct = 6  # Maximum Channel Width (%)
    min_strength = 1  # Minimum Strength
    max_num_sr = 6  # Maximum Number of S/R to Show
    plotSupportAndRessitent(ticker=ticker,prd=prd,loopback=loopback,channel_width_pct=channel_width_pct,min_strength=min_strength,max_num_sr=max_num_sr)


 
if __name__ == "__main__":
    # main(ticker="WEBELSOLAR")
    main(ticker="TATATECH")


