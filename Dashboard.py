import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import time
import plotly.express as px

# Import local modules
from PortFolioAnlayis import AllPortfolioStocksData, SRChannels, price_level_story
from Scraper.ScrrenerScraping import scrape_stock_data
from PlotingCode.PlotCandles import PlotChart
from DataLoad import getTickerFromName

st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- Helper Functions ---

@st.cache_data
def load_portfolio_data():
    """Loads portfolio data using the existing function."""
    return AllPortfolioStocksData()

def get_sr_analysis(df, sname):
    """Calculates SR zones and story for a stock."""
    sr = SRChannels(
        period=10,
        channel_width_percentage=6,
        min_strength=1,
        max_num_sr=6,
        loopback=365,
        SRSelection="Nearest",
        addstrengh=True
    )
    sr_zones = sr.getSupportAndRessitent(df)
    story = price_level_story(df, sr_zones)
    return sr_zones, story


def fig_to_base64(fig):
    """Converts a matplotlib figure to a base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_str

def generate_sparkline(df):
    """Generates a small sparkline chart for the last 90 days."""
    fig, ax = plt.subplots(figsize=(2, 0.5))
    data = df[-90:]
    ax.plot(data.index, data['Close'], color='blue', linewidth=1)
    ax.axis('off')
    return fig_to_base64(fig)

def generate_large_chart(df, ticker):
    """Generates a large candle chart with SR zones."""
    sr_zones, story = get_sr_analysis(df, ticker)
    try:
        # PlotChart returns a figure
        fig = PlotChart(df[-365:], Trend=f"{ticker} ({df.iloc[-1]['Close']:.2f})\n{story}", Bars=sr_zones, addCloseLine=True)
        return fig_to_base64(fig)
    except Exception as e:
        print(f"Error generating chart for {ticker}: {e}")
        return "" 

def calculate_period_metrics(df, months):
    """Calculates High, Low, and Growth % for the last n months."""
    try:
        if months == 0: 
             period_df = df
        else:
            days = months * 30
            start_date = df.index[-1] - pd.Timedelta(days=days)
            period_df = df[df.index >= start_date]
        
        if period_df.empty:
            return {"high": "N/A", "low": "N/A", "growth": "N/A"}
            
        max_high = period_df['High'].max()
        min_low = period_df['Low'].min()
        
        # Price at that time (start of period)
        # We take the first available close price in the period
        start_price = period_df.iloc[0]['Close']
        current_price = df.iloc[-1]['Close']
        
        growth = 0.0
        if start_price != 0:
            growth = ((current_price - start_price) / start_price) * 100
            
        high_diff = 0.0
        if max_high != 0:
            high_diff = ((current_price - max_high) / max_high) * 100
            
        low_diff = 0.0
        if min_low != 0:
            low_diff = ((current_price - min_low) / min_low) * 100
            
        return {
            "high": max_high,
            "low": min_low,
            "growth": growth,
            "high_diff": high_diff,
            "low_diff": low_diff
        }
    except Exception as e:
        print(f"Error calc metrics: {e}")
        return {"high": "N/A", "low": "N/A", "growth": "N/A"}

def generate_fundamental_chart(data_dict, title, is_sparkline=True):
    """Generates a chart for fundamental data (EPS, Holdings)."""
    if not data_dict or not isinstance(data_dict, dict):
        return ""
        
    try:
        # Parse data
        dates = []
        values = []
        for k, v in data_dict.items():
            # Try to parse date, assume format like "Mar 2014" or "Dec 2022"
            try:
                # Handle "TTM" or other non-date keys if necessary, usually they are at the end
                if k == "TTM": continue 
                
                # Simple parsing logic or use pd.to_datetime if format is standard
                # Let's use a dummy day 1 for parsing
                dt = pd.to_datetime(k, format='%b %Y', errors='coerce')
                if pd.notnull(dt):
                    dates.append(dt)
                    values.append(float(v) if v is not None else 0.0)
            except:
                continue
                
        if not dates: return ""
        
        # Sort by date
        sorted_data = sorted(zip(dates, values))
        dates, values = zip(*sorted_data)
        
        figsize = (2, 0.5) if is_sparkline else (8, 4)
        fig, ax = plt.subplots(figsize=figsize)
        
        ax.plot(dates, values, marker='o', markersize=2 if is_sparkline else 4, linestyle='-')
        
        if is_sparkline:
            ax.axis('off')
        else:
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()
            
        return fig_to_base64(fig)
    except Exception as e:
        print(f"Error generating fund chart: {e}")
        return "" 

# --- CSS ---
st.markdown("""
<style>
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted black;
        cursor: pointer;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 800px;
        background-color: white;
        color: black;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: fixed; /* Fixed positioning to center on screen */
        z-index: 1000;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        opacity: 0;
        transition: opacity 0.3s;
        box-shadow: 0px 0px 20px rgba(0,0,0,0.7);
        border: 1px solid #ddd;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .stock-table {
        width: 100%;
        border-collapse: collapse;
    }
    .stock-table th, .stock-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .stock-table th {
        background-color: #f2f2f2;
    }
    .sparkline {
        width: 150px;
        height: 40px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Stock Analysis Dashboard")

# Load Data
with st.spinner("Loading Portfolio Data..."):
    portfolio_data, holding_data = load_portfolio_data()

if not portfolio_data:
    st.error("No portfolio data found.")
    st.stop()

# Check for query params for full page view
query_params = st.query_params
selected_ticker = query_params.get("ticker", None)

if selected_ticker:
    if st.button("Back to Dashboard"):
        st.query_params.clear()
        st.rerun()
    
    # Load specific ticker data
    # portfolio_data keys are now Company Names, so we need to map Ticker -> Name
    from DataLoad import getStockNameFromSymbol
    try:
        company_name = getStockNameFromSymbol(selected_ticker)
    except:
        company_name = selected_ticker

    st.title(f"{company_name} ({selected_ticker}) Full Analysis")

    if company_name in portfolio_data:
        df = portfolio_data[company_name]
        sr_zones, story = get_sr_analysis(df, selected_ticker)
        st.markdown(f"### Analysis Story\n{story}")
        
        # Use PlotChart directly for interactive/large view
        fig = PlotChart(df[-365:], Trend=f"{selected_ticker} ({df.iloc[-1]['Close']:.2f})", Bars=sr_zones, addCloseLine=True)
        st.pyplot(fig)
    else:
        st.error(f"Data for {selected_ticker} (Name: {company_name}) not found.")

else:
    # Dashboard View
    tickers = sorted(list(portfolio_data.keys())) # Process all tickers


    # --- HTML Helpers ---
    def fmt_metrics(metrics):
        high = metrics['high']
        low = metrics['low']
        growth = metrics['growth']
        high_diff = metrics.get('high_diff', 0)
        low_diff = metrics.get('low_diff', 0)
        
        if high == "N/A": return "N/A"
        
        growth_color = "green" if growth >= 0 else "red"
        growth_str = f"{growth:+.1f}%"
        
        return f"""
        <div style="line-height:1.2">
            <span style="color:{growth_color}; font-weight:bold">{growth_str}</span><br>
            <span style="font-size:0.8em; color:#555">
                H:{high:.0f} <span style="color:red">({high_diff:+.1f}%)</span><br>
                L:{low:.0f} <span style="color:green">({low_diff:+.1f}%)</span>
            </span>
        </div>
        """

    def fund_cell(data_obj, ticker_symbol=None, section_anchor=None):
        val = data_obj['val']
        spark = data_obj['spark']
        large = data_obj['large']
        
        content = f"{val}"
        if ticker_symbol and section_anchor:
             content = f'<a href="https://www.screener.in/company/{ticker_symbol}/#{section_anchor}" target="_blank" style="color:blue; text-decoration:underline;">{val}</a>'

        if not spark:
            return content
            
        spark_img = f"data:image/png;base64,{spark}"
        large_img = f"data:image/png;base64,{large}"
        return f"""
<div class="tooltip">
    {content} <br>
    <img src="{spark_img}" class="sparkline" style="width:50px;height:15px;"/>
    <span class="tooltiptext">
        <img src="{large_img}" style="width:100%"/>
    </span>
</div>
"""

    def generate_row_html(row):
        ticker_display = row['Ticker'] # Company Name
        ticker_symbol = getTickerFromName(ticker_display) # Symbol
        sparkline = f"data:image/png;base64,{row['Sparkline']}"
        large_chart = f"data:image/png;base64,{row['LargeChart']}"
        
        # Holding Data
        qty = row['Holding']['Qty']
        avg_price = row['Holding']['AvgPrice']
        pnl = row['Holding']['PnL']
        pnl_pct = row['Holding']['PnLPct']
        
        pnl_color = "green" if pnl >= 0 else "red"
        pnl_str = f"{pnl:,.0f}"
        pnl_pct_str = f"{pnl_pct:+.1f}%"
        
        holding_html = ""
        if qty > 0:
            holding_html = f"""
            <div style="font-size:0.9em; line-height:1.2">
                Qty: {qty}<br>
                Avg: {avg_price:.1f}<br>
                <span style="color:{pnl_color}; font-weight:bold">{pnl_str} ({pnl_pct_str})</span>
            </div>
            """
        else:
            holding_html = "-"

        return f"""
<tr>
    <td>
        <div class="tooltip">
            <a href="https://www.screener.in/company/{ticker_symbol}/" target="_blank" style="text-decoration:none; color:inherit; font-weight:bold;">{ticker_display}</a>
            <br>
            <a href="https://in.tradingview.com/chart/?symbol={ticker_symbol}" target="_blank" style="font-size:0.8em; color:blue; text-decoration:none;">[TradingView]</a>
            <span class="tooltiptext">
                <h3>{ticker_display} Analysis</h3>
                <img src="{large_chart}" style="width:100%"/>
            </span>
        </div>
    </td>
    <td>
        <div class="tooltip">
            <a href="?ticker={ticker_symbol}" target="_self">
                <img src="{sparkline}" class="sparkline"/>
            </a>
            <span class="tooltiptext">
                 <img src="{large_chart}" style="width:100%"/>
            </span>
        </div>
    </td>
    <td>{row['Price']:.2f}</td>
    <td>{holding_html}</td>
    <td>{fmt_metrics(row['Metrics']['1M'])}</td>
    <td>{fmt_metrics(row['Metrics']['3M'])}</td>
    <td>{fmt_metrics(row['Metrics']['6M'])}</td>
    <td>{fmt_metrics(row['Metrics']['1Y'])}</td>
    <td>{fmt_metrics(row['Metrics']['3Y'])}</td>
    <td>{fmt_metrics(row['Metrics']['5Y'])}</td>
    <td>{fund_cell(row['Fundamentals']['EPS'])}</td>
    <td>{row['Fundamentals']['PE']}</td>
    <td>{row['Fundamentals']['ROCE']}</td>
    <td>{fund_cell(row['Fundamentals']['Promoter'], ticker_symbol, "shareholding")}</td>
    <td>{fund_cell(row['Fundamentals']['FII'], ticker_symbol, "shareholding")}</td>
    <td>{fund_cell(row['Fundamentals']['DII'], ticker_symbol, "shareholding")}</td>
</tr>
"""

    table_header = '''
    <table class="stock-table">
    <tr>
        <th>Ticker</th>
        <th>Trend (90D)</th>
        <th>Price</th>
        <th>Holding</th>
        <th>1M (Gr | H/L)</th>
        <th>3M (Gr | H/L)</th>
        <th>6M (Gr | H/L)</th>
        <th>1Y (Gr | H/L)</th>
        <th>3Y (Gr | H/L)</th>
        <th>5Y (Gr | H/L)</th>
        <th>EPS</th>
        <th>PE</th>
        <th>ROCE</th>
        <th>Promoter</th>
        <th>FII</th>
        <th>DII</th>
    </tr>
    '''

    # Auto-load data if not in session state
    if 'table_data' not in st.session_state:
        table_data = []
        rows_html = ""
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        table_placeholder = st.empty()
        
        # Initial render of empty table
        table_placeholder.markdown(table_header + "</table>", unsafe_allow_html=True)
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"Processing {ticker} ({i+1}/{len(tickers)})...")
            df = portfolio_data[ticker]
            
            # Scrape
            fund_data = scrape_stock_data(ticker) or {}
            
            # Sparkline
            sparkline_b64 = generate_sparkline(df)
            
            # Large Chart
            large_chart_b64 = generate_large_chart(df, ticker)
            
            # Percentage Down/Up Metrics
            def calc_metrics(months):
                return calculate_period_metrics(df, months)
                
            metrics = {
                "1M": calc_metrics(1),
                "3M": calc_metrics(3),
                "6M": calc_metrics(6),
                "1Y": calc_metrics(12),
                "3Y": calc_metrics(36),
                "5Y": calc_metrics(60)
            }
            
            # Holding Info
            qty = 0
            avg_price = 0.0
            pnl = 0.0
            pnl_pct = 0.0
            
            if ticker in holding_data:
                qty, avg_price = holding_data[ticker]
                current_price = df.iloc[-1]['Close']
                if qty > 0:
                    current_val = qty * current_price
                    invested_val = qty * avg_price
                    pnl = current_val - invested_val
                    if invested_val > 0:
                        pnl_pct = (pnl / invested_val) * 100
            
            # Fundamental Data Charts
            eps_data = fund_data.get("EPS", {})
            promoter_data = fund_data.get("Promoter Holding", {})
            fii_data = fund_data.get("FII Holding", {})
            dii_data = fund_data.get("DII Holding", {})
            
            eps_spark = generate_fundamental_chart(eps_data, "EPS Trend", is_sparkline=True)
            eps_large = generate_fundamental_chart(eps_data, "EPS Trend", is_sparkline=False)
            
            promoter_spark = generate_fundamental_chart(promoter_data, "Promoter Holding", is_sparkline=True)
            promoter_large = generate_fundamental_chart(promoter_data, "Promoter Holding", is_sparkline=False)
            
            fii_spark = generate_fundamental_chart(fii_data, "FII Holding", is_sparkline=True)
            fii_large = generate_fundamental_chart(fii_data, "FII Holding", is_sparkline=False)
            
            dii_spark = generate_fundamental_chart(dii_data, "DII Holding", is_sparkline=True)
            dii_large = generate_fundamental_chart(dii_data, "DII Holding", is_sparkline=False)

            # Extract metrics (current values)
            def get_last_val(d):
                if not d: return "N/A"
                try:
                    sorted_keys = sorted(d.keys(), key=lambda x: pd.to_datetime(x, format='%b %Y', errors='coerce') if x != 'TTM' else pd.Timestamp.max)
                    last_key = sorted_keys[-1]
                    return d[last_key]
                except: return "N/A"

            current_eps = get_last_val(fund_data.get("EPS", []))
            current_promoter = get_last_val(fund_data.get("Promoter Holding", []))
            current_fii = get_last_val(fund_data.get("FII Holding", []))
            current_dii = get_last_val(fund_data.get("DII Holding", []))
            
            pe = fund_data.get("PE", "N/A")
            roce = fund_data.get("ROCE", "N/A")
            
            row_data = {
                "Ticker": ticker,
                "Sparkline": sparkline_b64,
                "LargeChart": large_chart_b64,
                "Price": df.iloc[-1]['Close'],
                "Metrics": metrics,
                "Holding": {
                    "Qty": qty,
                    "AvgPrice": avg_price,
                    "PnL": pnl,
                    "PnLPct": pnl_pct
                },
                "Fundamentals": {
                    "EPS": {"val": current_eps, "spark": eps_spark, "large": eps_large},
                    "Promoter": {"val": current_promoter, "spark": promoter_spark, "large": promoter_large},
                    "FII": {"val": current_fii, "spark": fii_spark, "large": fii_large},
                    "DII": {"val": current_dii, "spark": dii_spark, "large": dii_large},
                    "PE": pe,
                    "ROCE": roce
                }
            }
            
            table_data.append(row_data)
            
            # Incremental Render
            rows_html += generate_row_html(row_data)
            table_placeholder.markdown(table_header + rows_html + "</table>", unsafe_allow_html=True)
            
            progress_bar.progress((i + 1) / len(tickers))
        
        status_text.empty()
        st.session_state['table_data'] = table_data

    else:
        # Render from session state
        rows_html = ""
        for row in st.session_state['table_data']:
            rows_html += generate_row_html(row)
        
        st.markdown(table_header + rows_html + "</table>", unsafe_allow_html=True)

