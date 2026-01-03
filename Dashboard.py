import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import time
import plotly.express as px

# Import local modules
from PortFolioAnlayis import AllPortfolioStocksData, SRChannels, price_level_story, split_sr_zones
from Scraper.ScrrenerScraping import scrape_stock_data
from PlotingCode.PlotCandles import PlotChart
from DataLoad import getTickerFromName

st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# --- Helper Functions ---

@st.cache_data(ttl="1d")
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

@st.cache_data(ttl="1d")
def generate_sparkline(df):
    """Generates a small sparkline chart for the last 90 days."""
    fig, ax = plt.subplots(figsize=(2, 0.5))
    data = df[-90:]
    ax.plot(data.index, data['Close'], color='blue', linewidth=1)
    ax.axis('off')
    return fig_to_base64(fig)

@st.cache_data(ttl="1d")
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

@st.cache_data(ttl="1d")
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

def get_last_val(d):
    """Extracts the last value from a date-keyed dictionary."""
    if not d: return "N/A"
    try:
        # Sort by date
        sorted_keys = sorted(d.keys(), key=lambda x: pd.to_datetime(x, format='%b %Y', errors='coerce') if x != 'TTM' else pd.Timestamp.max)
        last_key = sorted_keys[-1]
        return d[last_key]
    except: return "N/A"

@st.cache_data(ttl="1d")
def get_cached_stock_data(ticker):
    """Cached wrapper for scraping stock data."""
    return scrape_stock_data(ticker)

def generate_reason(fund_data):
    """Generates a reason string based on negative indicators."""
    reasons = []
    if not fund_data: return ""
    
    # Helper to check decrease
    def check_decrease(data_dict):
        if not data_dict or len(data_dict) < 2: return False
        try:
            sorted_keys = sorted(data_dict.keys(), key=lambda x: pd.to_datetime(x, format='%b %Y', errors='coerce') if x != 'TTM' else pd.Timestamp.max)
            values = [float(data_dict[k]) for k in sorted_keys if data_dict[k] is not None]
            if len(values) >= 2:
                if values[-1] < values[-2]: return True
        except: pass
        return False

    # EPS
    eps_data = fund_data.get("EPS", {})
    current_eps = get_last_val(eps_data)
    if isinstance(current_eps, (int, float)):
        if current_eps < 0: reasons.append("Negative EPS")
        elif check_decrease(eps_data): reasons.append("Decreasing EPS")
    
    # Holdings
    if check_decrease(fund_data.get("Promoter Holding", {})): reasons.append("Decreasing Promoter Holding")
    if check_decrease(fund_data.get("FII Holding", {})): reasons.append("Decreasing FII Holding")
    if check_decrease(fund_data.get("DII Holding", {})): reasons.append("Decreasing DII Holding")
    if check_decrease(fund_data.get("EPS", {})): reasons.append("Decreasing EPS")
    
    return ", ".join(reasons)

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

    # --- Filters ---
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_shareholding = st.checkbox("Shareholding Decrease (Promoter, FII, DII)")
        with col2:
            filter_price = st.checkbox("Price Proximity Filter")
        with col3:
            near_low_pct = st.number_input("Near 1Y Low (%)", min_value=0.0, value=5.0, step=0.5, disabled=not filter_price)
        with col4:
            far_high_pct = st.number_input("Far from 1Y High (%)", min_value=0.0, value=25.0, step=1.0, disabled=not filter_price)

    def check_shareholding_decrease(fund_data):
        """Checks if Promoter, FII, AND DII have at least one decrease."""
        if not fund_data: return False
        
        def has_decrease(data_dict):
            if not data_dict or len(data_dict) < 2: return False
            # Sort by date
            try:
                sorted_keys = sorted(data_dict.keys(), key=lambda x: pd.to_datetime(x, format='%b %Y', errors='coerce') if x != 'TTM' else pd.Timestamp.max)
                values = [float(data_dict[k]) for k in sorted_keys if data_dict[k] is not None]
                for i in range(1, len(values)):
                    if values[i] < values[i-1]:
                        return True
                return False
            except:
                return False

        p_dec = has_decrease(fund_data.get("Promoter Holding", {}))
        f_dec = has_decrease(fund_data.get("FII Holding", {}))
        d_dec = has_decrease(fund_data.get("DII Holding", {}))
        
        return p_dec and f_dec and d_dec

    def check_price_proximity(df, low_pct, high_pct):
        """Checks if Price is near 1Y Low and far from 1Y High."""
        if df.empty: return False
        
        # Last 1 Year
        start_date = df.index[-1] - pd.Timedelta(days=365)
        period_df = df[df.index >= start_date]
        if period_df.empty: return False
        
        current_price = df.iloc[-1]['Close']
        low_1y = period_df['Low'].min()
        high_1y = period_df['High'].max()
        
        if low_1y == 0: return False
        
        # Near 1Y Low (within low_pct)
        # e.g. if low_pct is 5, price <= low * 1.05
        near_low = current_price <= (low_1y * (1 + low_pct/100))
        
        # Far from 1Y High (more than high_pct away)
        # e.g. if high_pct is 25, High >= Current * 1.25
        far_high = high_1y >= (current_price * (1 + high_pct/100))
        
        return near_low and far_high

    # Filter Tickers
    # Initialize processed data cache
    if 'processed_data' not in st.session_state:
        st.session_state['processed_data'] = {}
    
    processed_data = st.session_state['processed_data']

    # Progress Bar at Top
    progress_bar = st.progress(0)
    status_text = st.empty()

    filtered_tickers = []
    if filter_shareholding or filter_price:
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"Filtering {ticker} ({i+1}/{len(tickers)})...")
            progress_bar.progress((i + 1) / len(tickers))
            
            keep = True
            
            # We need data for filtering
            df = portfolio_data[ticker]
            # Use cached wrapper
            fund_data = get_cached_stock_data(ticker) or {} 
            
            if filter_shareholding:
                if not check_shareholding_decrease(fund_data):
                    keep = False
            
            if keep and filter_price:
                if not check_price_proximity(df, near_low_pct, far_high_pct):
                    keep = False
            
            if keep:
                filtered_tickers.append(ticker)
        
        tickers = filtered_tickers
        st.write(f"Showing {len(tickers)} stocks after filtering.")
    
    # --- Export Section ---
    with st.expander("Export Data", expanded=False):
        if st.button("Generate Export Report for Selected Rows"):
            selected_export_tickers = []
            for ticker in tickers:
                if st.session_state.get(f"select_{ticker}", False):
                    selected_export_tickers.append(ticker)
            
            if not selected_export_tickers:
                st.warning("No stocks selected. Please check the boxes in the table rows.")
            else:
                export_data = []
                progress_bar_export = st.progress(0)
                status_text_export = st.empty()
                
                for i, ticker in enumerate(selected_export_tickers):
                    status_text_export.text(f"Exporting {ticker} ({i+1}/{len(selected_export_tickers)})...")
                    progress_bar_export.progress((i + 1) / len(selected_export_tickers))
                    
                    df = portfolio_data[ticker]
                    fund_data = get_cached_stock_data(ticker) or {}
                    
                    # Support
                    current_price = df.iloc[-1]['Close']
                    sr_zones, story = get_sr_analysis(df, ticker)
                    supports, _ = split_sr_zones(sr_zones, current_price)
                    support_text = f"{supports[0]['low']:.2f}" if supports else "N/A"
                    
                    # Reason
                    reason = generate_reason(fund_data)
                    
                    # Links
                    ticker_symbol = getTickerFromName(ticker)
                    screener_link = f'=HYPERLINK("https://www.screener.in/company/{ticker_symbol}/", "Screener")'
                    tv_link = f'=HYPERLINK("https://in.tradingview.com/chart/?symbol={ticker_symbol}", "TradingView")'
                    
                    export_data.append({
                        "Stock Name": ticker,
                        "Immediate Support": support_text,
                        "Reason (Negative Indicators)": reason,
                        "Story": story,
                        "Screener Link": screener_link,
                        "TradingView Link": tv_link
                    })
                
                if export_data:
                    export_df = pd.DataFrame(export_data)
                    
                    # Export to Excel
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='Stock Analysis')
                    
                    buffer.seek(0)
                    
                    st.download_button(
                        label="Download Export Excel",
                        data=buffer,
                        file_name='stock_analysis_export.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
                    st.success(f"Export Report Generated for {len(selected_export_tickers)} stocks! Click above to download.")
                
                status_text_export.empty()
                progress_bar_export.empty()
    
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

    # Column Config
    # Checkbox, Ticker, Trend, Price, Support, Holding, 1M, 3M, 6M, 1Y, 3Y, 5Y, EPS, PE, ROCE, Prom, FII, DII
    col_ratios = [0.5, 2, 1.5, 1, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1, 1, 1.5, 1.5, 1.5]
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Header
    cols = st.columns(col_ratios)
    headers = ["Sel", "Ticker", "Trend", "Price", "Support", "Holding", "1M", "3M", "6M", "1Y", "3Y", "5Y", "EPS", "PE", "ROCE", "Prom", "FII", "DII"]
    for col, h in zip(cols, headers):
        col.markdown(f"**{h}**")
    
    st.markdown("---")
    
    # Iterate over the (potentially filtered) tickers
    for i, ticker in enumerate(tickers):
        # Check if already processed
        if ticker in processed_data:
            row_data = processed_data[ticker]
        else:
            status_text.text(f"Processing {ticker} ({i+1}/{len(tickers)})...")
            
            df = portfolio_data[ticker]
            
            # Scrape
            fund_data = get_cached_stock_data(ticker) or {}
            
            # Sparkline
            sparkline_b64 = generate_sparkline(df)
            
            # Large Chart
            large_chart_b64 = generate_large_chart(df, ticker)
            
            # Support Analysis
            current_price = df.iloc[-1]['Close']
            sr_zones, _ = get_sr_analysis(df, ticker)
            supports, _ = split_sr_zones(sr_zones, current_price)
            
            support_text = "N/A"
            support_dist = 0.0
            
            if supports:
                s = supports[0] # Nearest support
                support_text = f"{s['low']:.2f}"
                # Distance from high of support zone
                support_dist = ((current_price - s['high']) / s['high']) * 100
                
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
                # current_price already defined above
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
                "Price": current_price,
                "Support": {"text": support_text, "dist": support_dist},
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
            
            # Store in session state cache
            processed_data[ticker] = row_data
            progress_bar.progress((i + 1) / len(tickers))

        # Render Row
        cols = st.columns(col_ratios)
        
        # 1. Checkbox
        with cols[0]:
            st.checkbox("Select", key=f"select_{ticker}", label_visibility="collapsed")
            
        # 2. Ticker
        ticker_display = row_data['Ticker']
        ticker_symbol = getTickerFromName(ticker_display)
        large_chart = f"data:image/png;base64,{row_data['LargeChart']}"
        cols[1].markdown(f"""
        <div class="tooltip">
            <a href="https://www.screener.in/company/{ticker_symbol}/" target="_blank" style="text-decoration:none; color:inherit; font-weight:bold;">{ticker_display}</a>
            <span class="tooltiptext">
                <h3>{ticker_display} Analysis</h3>
                <img src="{large_chart}" style="width:100%"/>
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. Trend
        sparkline = f"data:image/png;base64,{row_data['Sparkline']}"
        cols[2].markdown(f"""
        <div class="tooltip">
            <a href="?ticker={ticker_symbol}" target="_self">
                <img src="{sparkline}" class="sparkline"/>
            </a>
            <br>
            <a href="https://in.tradingview.com/chart/?symbol={ticker_symbol}" target="_blank" style="font-size:0.8em; color:blue; text-decoration:none;">[TradingView]</a>
            <span class="tooltiptext">
                 <img src="{large_chart}" style="width:100%"/>
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. Price
        cols[3].markdown(f"{row_data['Price']:.2f}")
        
        # 5. Support
        support_info = row_data['Support']
        support_color = "green" if abs(support_info['dist']) < 5 else "black"
        cols[4].markdown(f"""
        <span style="color:{support_color}">{support_info['text']}</span><br>
        <span style="font-size:0.8em; color:#555">({support_info['dist']:.1f}%)</span>
        """, unsafe_allow_html=True)
        
        # 6. Holding
        holding = row_data['Holding']
        if holding['Qty'] > 0:
            pnl_color = "green" if holding['PnL'] >= 0 else "red"
            cols[5].markdown(f"""
            <div style="font-size:0.9em; line-height:1.2">
                Qty: {holding['Qty']}<br>
                Avg: {holding['AvgPrice']:.1f}<br>
                <span style="color:{pnl_color}; font-weight:bold">{holding['PnL']:,.0f} ({holding['PnLPct']:+.1f}%)</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            cols[5].markdown("-")
            
        # 7-12. Metrics
        cols[6].markdown(fmt_metrics(row_data['Metrics']['1M']), unsafe_allow_html=True)
        cols[7].markdown(fmt_metrics(row_data['Metrics']['3M']), unsafe_allow_html=True)
        cols[8].markdown(fmt_metrics(row_data['Metrics']['6M']), unsafe_allow_html=True)
        cols[9].markdown(fmt_metrics(row_data['Metrics']['1Y']), unsafe_allow_html=True)
        cols[10].markdown(fmt_metrics(row_data['Metrics']['3Y']), unsafe_allow_html=True)
        cols[11].markdown(fmt_metrics(row_data['Metrics']['5Y']), unsafe_allow_html=True)
        
        # 13-18. Fundamentals
        cols[12].markdown(fund_cell(row_data['Fundamentals']['EPS']), unsafe_allow_html=True)
        cols[13].markdown(f"{row_data['Fundamentals']['PE']}")
        cols[14].markdown(f"{row_data['Fundamentals']['ROCE']}")
        cols[15].markdown(fund_cell(row_data['Fundamentals']['Promoter'], ticker_symbol, "shareholding"), unsafe_allow_html=True)
        cols[16].markdown(fund_cell(row_data['Fundamentals']['FII'], ticker_symbol, "shareholding"), unsafe_allow_html=True)
        cols[17].markdown(fund_cell(row_data['Fundamentals']['DII'], ticker_symbol, "shareholding"), unsafe_allow_html=True)
        
        st.markdown("---")
    
    status_text.success("Processing Completed!")
