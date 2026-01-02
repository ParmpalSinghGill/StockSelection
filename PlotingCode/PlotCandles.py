import datetime,warnings #,talib
warnings.filterwarnings("ignore")
from matplotlib import pyplot as plt
import pandas as pd
import mplfinance as mpf
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle


# def PlotCandles(df,figratio=(30, 8),Trend=None,xrotation=45,nbins=30):
# 	df.index = df.index.map(lambda x: x.to_pydatetime())
# 	title=f'Candlestick chart for {Trend}' if Trend else "Candlestick"
# 	fig, axlist=mpf.plot(df, type='candle', style='charles', title=title,
# 	         ylabel='Price ', volume=True, datetime_format='%y-%m-%d',
# 	         xrotation=xrotation, show_nontrading=True,returnfig=True, figratio=figratio)
# 	axlist[0].xaxis.set_major_locator(plt.MaxNLocator(nbins=nbins))


def PlotCandles(df,figratio=(30, 8),Trend=None,xrotation=45,nbins=30,addIndicatorSpace=False,sharex=True):
	df.index = df.index.map(lambda x: x.to_pydatetime())
	# title=f'Candlestick chart for {Trend}' if Trend else "Candlestick"
	title=f'{Trend}' if Trend else "Candlestick"
	if addIndicatorSpace:
		fig, (ax_candle, ax_volumn,ax_indicater) = plt.subplots(3, 1, figsize=(20, 10), sharex=sharex, gridspec_kw={'height_ratios': [3, 1,1], 'hspace': 0})
		mpf.plot(df, type='candle', style='charles',ax=ax_candle,ylabel='Price ', volume=ax_volumn, datetime_format='%y-%m-%d',
		         xrotation=xrotation, show_nontrading=True, figratio=figratio)
		fig.suptitle(title)
		ax_candle.grid(True)
		ax_volumn.grid(True)
		ax_candle.grid(True)
		ax_indicater.grid(True)
		ax_candle.xaxis.set_major_locator(plt.MaxNLocator(nbins=nbins))
		ax_indicater.tick_params(axis='x', rotation=xrotation)
		for bar in ax_volumn.patches:
			bar.set_width(0.8)  # Set the desired width here
		return fig, (ax_candle, ax_volumn,ax_indicater)
	else:
		fig, (ax_candle, ax_volumn) = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1], 'hspace': 0})
		mpf.plot(df, type='candle', style='charles',ax=ax_candle,
		         ylabel='Price ', volume=ax_volumn, datetime_format='%y-%m-%d',
		         xrotation=xrotation, show_nontrading=True, figratio=figratio)
		fig.suptitle(title)
		ax_candle.grid(True)
		ax_volumn.grid(True)
		ax_candle.grid(True)
		ax_candle.xaxis.set_major_locator(plt.MaxNLocator(nbins=nbins))
		ax_volumn.tick_params(axis='x', rotation=xrotation)
		return fig, (ax_candle, ax_volumn)


def PlotChart(df,Trend=None,TrendBox=None,LineS=None,Bars=None,addCloseLine=True):
	# fig, (ax_candle,ax_volumn,ax_indicater)=PlotCandles(df,figratio=(30, 8),Trend=Trend,addIndicatorSpace=True)
	fig, (ax_candle,ax_volumn)=PlotCandles(df,figratio=(30, 8),Trend=Trend)
	lastclose=df["Close"][-1]
	if addCloseLine:
		ax_candle.axhline(y=lastclose, color='black', linestyle='-', linewidth=1.5)

	if LineS is not None:
		for line in LineS:
			ax_candle.axhline(y=line, color='red', linestyle='--', linewidth=1.5)


	if TrendBox is not None :
		TrendStart , TrnedEnd=TrendBox
		highlight_start_mdate = mdates.date2num(pd.to_datetime(TrendStart))
		highlight_end_mdate = mdates.date2num(pd.to_datetime(TrnedEnd))
		TrendData=df[(TrendStart<=df.index)&(df.index<=TrnedEnd)]
		# Get the price range to cover with the box (you can adjust the vertical limits as needed)
		low_price = TrendData['Low'].min()  # Lowest price in the data range
		high_price = TrendData['High'].max()  # Highest price in the data range
		# Create a rectangle box over the selected date range
		rect = Rectangle((highlight_start_mdate, low_price),  # (x, y) lower-left corner
		                 highlight_end_mdate - highlight_start_mdate,  # width (difference in date)
		                 high_price - low_price,  # height (difference in price)
		                 linewidth=1, edgecolor='red', facecolor='yellow', alpha=0.3)  # Rectangle style

		# Add the rectangle to the plot
		ax_candle.add_patch(rect)

	if Bars is not None :
		for bar in Bars:
			high_price,low_price=bar[:2]
			color="green" if lastclose>high_price else "red" if lastclose<low_price else "lime"
			TrendStart , TrnedEnd=df.index[0],df.index[-1]
			highlight_start_mdate = mdates.date2num(pd.to_datetime(TrendStart))
			highlight_end_mdate = mdates.date2num(pd.to_datetime(TrnedEnd))
			# Create a rectangle box over the selected date range
			rect = Rectangle((highlight_start_mdate, low_price),  # (x, y) lower-left corner
			                 highlight_end_mdate - highlight_start_mdate,  # width (difference in date)
			                 high_price - low_price,  # height (difference in price)
			                 linewidth=1, edgecolor=color, facecolor=color, alpha=0.3)  # Rectangle style
			# Add the rectangle to the plot
			ax_candle.add_patch(rect)



	# Set date format and frequency of the labels
	intervals=mdates.WeekdayLocator(interval=1) if df.shape[0]<150 else mdates.MonthLocator(interval=1) if df.shape[0]<1000 else mdates.MonthLocator(interval=3) if df.shape[0]<2000 else mdates.MonthLocator(interval=6)
	ax_candle.xaxis.set_major_locator(intervals)  # Show labels every week
	ax_candle.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))  # Format labels as 'Year-Month-Day'

	# Rotate date labels to make them readable
	fig.autofmt_xdate()
	# Show the chart
	mpf.show()


def PlotTrend(findTrend,df,windowlenght=100,n=10,lastNDays=2,minmumMovepercent=15):
	if df.shape[0] < windowlenght - 10: return
	j=1
	for i in range(windowlenght, df.shape[0]):
		pastData = df[i-windowlenght:i]
		Trend,TrendStart, TrnedEnd=findTrend(pastData,n=n,lastNDays=lastNDays)
		if Trend==None: continue
		TrenDf=pastData[(pastData.index>=TrendStart) &(pastData.index<=TrnedEnd)]
		startprice, endprice = TrenDf.loc[TrenDf.index[0], "Close"], TrenDf.loc[TrenDf.index[-1], "Close"]
		# if Trend == "Down":
		# 	startprice, endprice = TrenDf.loc[TrenDf.index[0], "High"], TrenDf.loc[TrenDf.index[-1], "Low"]
		# else:
		# 	startprice, endprice = TrenDf.loc[TrenDf.index[0], "Low"], TrenDf.loc[TrenDf.index[-1], "High"]
		movepercent=abs(startprice-endprice)/startprice*100
		if movepercent<minmumMovepercent:continue
		ChartStart, ChartEnd = pastData.index[0], pastData.index[-1]
		# print(TrenDf)
		print(f"Chart Start {ChartStart} Chart End {ChartEnd}")
		print(f"Trend Start {TrendStart} Trend End {TrnedEnd}")
		StockText=f"From {startprice:.2f} to {endprice:.2f} ({abs(startprice-endprice)/startprice*100:.2f}%)"
		print(j,Trend,f"Stock Move From {startprice:.2f} to {endprice:.2f} That is {movepercent:.2}%")
		PlotChart(pastData, f"{Trend} from {TrendStart}--->{TrnedEnd} {StockText}",(TrendStart,TrnedEnd))
		j+=1
		# exit()


def PlotCandleAndMACD(df,Key=None):
	fig, (ax_candle,ax_volumn,ax_macd)=PlotCandles(df,Trend=Key,figratio=(30, 10),xrotation=45,nbins=30,addIndicatorSpace=True,sharex=True)
	ax_macd.plot(df.index, df['Fast'], label='Fast', color='Green')
	ax_macd.plot(df.index, df['Slow'], label='Slow', color='Red')
	ax_macd.bar(df.index, df['Signal'], color=['green' if val >= 0 else 'red' for val in df['Signal']], width=0.7,label='Signal')
	ax_macd.xaxis.set_major_locator(plt.MaxNLocator(nbins=20))
	ax_macd.set_ylabel("MACD")
	ax_macd.grid(True)
	return ax_candle,ax_volumn,ax_macd


def PlotMACD(df,Key=None,n=120,fastperiod=12,slowperiod=26,signalperiod=9):
	fast, slow, signal = talib.MACD(df["Close"].values, fastperiod=fastperiod, slowperiod=slowperiod,signalperiod=signalperiod)
	macd=pd.DataFrame({"Fast":fast, "Slow":slow, "Signal":signal},index=df.index)
	df=pd.concat((df,macd),axis=1)[-n:]
	PlotCandleAndMACD(df,Key=Key)
	mpf.show()

def getTradeTitile(row,key):
	if row['SelPrice'] > row['BuyPrice']:
		profit = (row['SelPrice'] - row['BuyPrice']) / row['BuyPrice'] * 100
		title = f"{key} Profit {profit:.2f}%" + (" Hit Target" if row["Reason"] == "Target" else f" Sell Signal")
	else:
		loss = (row['BuyPrice'] - row['SelPrice']) / row['BuyPrice'] * 100
		title = f"{key} Loss {loss:.2f}%" + (" Hit Stoploss" if row["Reason"] == "StopLoss" else f" Sell Signal")
	return title

def PlotMACDForTrade(df,position,Key=None,n=10,fastperiod=12,slowperiod=26,signalperiod=9):
	title=getTradeTitile(position, Key)
	Start,End=position["BuyDate"], position["SelDate"]
	fast, slow, signal = talib.MACD(df["Close"].values, fastperiod=fastperiod, slowperiod=slowperiod,signalperiod=signalperiod)
	macd=pd.DataFrame({"Fast":fast, "Slow":slow, "Signal":signal},index=df.index)
	df=pd.concat((df,macd),axis=1)
	stardDate=datetime.datetime.strptime(Start,"%Y-%m-%d") if isinstance(Start,str) else Start
	enddDate=datetime.datetime.strptime(End,"%Y-%m-%d") if isinstance(End,str) else End
	df=df[stardDate-datetime.timedelta(days=n):enddDate+datetime.timedelta(days=n)]
	TradeDf=df[stardDate:enddDate]
	ax_candle,ax_volumn,ax_macd=PlotCandleAndMACD(df,Key=title)
	highlight_start_mdate = mdates.date2num(pd.to_datetime(Start))
	highlight_end_mdate = mdates.date2num(pd.to_datetime(End))
	low_price,high_price=TradeDf["Low"].min(),TradeDf["High"].max()
	low_price,high_price=low_price,low_price*1.01
	print(highlight_start_mdate)
	rect = Rectangle((highlight_start_mdate, low_price),  # (x, y) lower-left corner
	                 highlight_end_mdate - highlight_start_mdate,  # width (difference in date)
	                 high_price - low_price,  # height (difference in price)
	                 linewidth=1, edgecolor='red', facecolor='yellow', alpha=0.3)  # Rectangle style
	ax_candle.add_patch(rect)
	mpf.show()


def PlotSupportAndRessitent(findSupportAndRessut,df,info=None):
	supportRessitent = findSupportAndRessut(df)
	if len(supportRessitent) == 0: return
	PlotChart(df, LineS=supportRessitent, Trend=info)


def PlotSupportAndRessitentForHistory(findSupportAndRessut,df,windowlenght=100,info=None):
	if df.shape[0] < windowlenght - 10: return
	for i in range(windowlenght, df.shape[0]):
		pastData = df[i-windowlenght:i]
		PlotSupportAndRessitent(findSupportAndRessut, pastData, info=None)

