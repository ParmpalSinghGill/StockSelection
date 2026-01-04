import pandas as pd
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

def get_us_targets_finviz(ticker):
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req)
        soup = BeautifulSoup(html, "html.parser")
        
        # Finviz stores ratings in a specific table class
        # Note: Class names change occasionally on Finviz
        ratings_table = soup.find(class_="fullview-ratings-outer")
        
        if ratings_table:
            rows = ratings_table.find_all('tr')
            data = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    date = cols[0].text
                    action = cols[1].text
                    firm = cols[2].text
                    rating = cols[3].text
                    target = cols[4].text # This column often has the price (e.g., 150 -> 180)
                    data.append([date, action, firm, rating, target])
            
            df = pd.DataFrame(data, columns=['Date', 'Action', 'Firm', 'Rating', 'Target Price'])
            print(f"\n--- Broker Targets for {ticker} (Source: Finviz) ---")
            print(df.head(10).to_string(index=False))
        else:
            print("Could not find ratings table.")
            
    except Exception as e:
        print(f"Error: {e}")

# Example for US Stock
get_us_targets_finviz("SVJN.NS")