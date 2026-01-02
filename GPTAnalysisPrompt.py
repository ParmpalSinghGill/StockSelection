def analyze_stock(stock_name):
    """
    Comprehensive Stock Analysis Template
    Usage Example: analyze_stock("AAPL")
    """

    prompt = f"""
    You are a professional financial analyst AI specializing in stock market research and long-term investment strategy.

    Analyze the stock: **{stock_name}**

    Perform a full analysis and return a detailed, structured report with the following sections:

    1. **Company Overview**
       - Briefly describe what the company does, its main business segments, and market position.
       - Mention major competitors and the sector it operates in.

    2. **Recent Performance Snapshot**
       - Current price, 52-week high/low, and recent price movement.
       - Key news/events influencing recent performance (earnings, leadership, macro trends).

    3. **Fundamental Analysis**
       - Key ratios: P/E, P/B, EPS, ROE, Debt-to-Equity, etc.
       - Revenue, profit, and margin trends (past 3–5 years).
       - Cash flow and balance sheet strength.
       - Insider and institutional sentiment.

    4. **Technical Analysis**
       - Trend direction (bullish/bearish/sideways).
       - Key support and resistance levels.
       - Important indicators: RSI, MACD, Moving Averages (20, 50, 200).
       - Momentum and volume insights.

    5. **Valuation Analysis**
       - Compare current valuation vs. peers and historical averages.
       - Determine whether the stock appears undervalued, fairly valued, or overvalued.

    6. **Macro & Sector Analysis**
       - Discuss broader industry trends and macroeconomic factors that impact the company.
       - Include any geopolitical or regulatory risks or tailwinds.

    7. **Risk Factors**
       - Summarize key financial, market, and operational risks.

    8. **Analyst Consensus & Sentiment**
       - Mention the general consensus from professional analysts (Buy/Hold/Sell if available).
       - Include any notable investor sentiment trends.

    9. **AI Recommendation Summary**
       - **Verdict:** Buy / Sell / Hold
       - **Confidence Level:** (1–100)
       - **If Buy:**
           - Suggested Buy Price Range
           - 1-Year Target Price
           - 3-Year Target Price
           - 5-Year Target Price
           - Expected annualized return (approx.)
       - **If Sell or Hold:**
           - Explain reasoning and what might change this stance.

    10. **Rationale (Why This Recommendation)**
        - Explain in plain English why this recommendation was made.
        - Combine quantitative reasoning (financial metrics, valuation) with qualitative insights (strategy, market position, growth prospects).

    Format output as a professional equity research report with markdown headers, bullet points, and short paragraphs.

    End with a one-sentence summary like:
    “Overall, {stock_name} is rated as a [Buy/Sell/Hold] with a confidence of XX due to [main reason].”
    **If Buy:**
           - Suggested Buy Price Range
           - 1-Year Target Price
           - 3-Year Target Price
           - 5-Year Target Price
           - Expected annualized return (approx.)
       - **If Sell or Hold:**
           - Explain reasoning and what might change this stance.

    """

    return prompt


print(analyze_stock("WIPRO LTD "))