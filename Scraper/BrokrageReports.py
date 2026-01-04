import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

class BrokerageReportExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def get_et_url(self, ticker):
        """
        Searches DuckDuckGo for the Economic Times stock page URL.
        Note: This may fail if DuckDuckGo blocks the request (returns 202).
        """
        queries = [
            f"site:economictimes.indiatimes.com {ticker} stock price",
            f"{ticker} share price economic times"
        ]
        
        endpoints = [
            "https://html.duckduckgo.com/html/",
            "https://lite.duckduckgo.com/lite/"
        ]
        
        for query in queries:
            for url in endpoints:
                data = {
                    "q": query
                }
                try:
                    time.sleep(random.uniform(1, 2))
                    response = requests.post(url, data=data, headers=self.headers)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, "html.parser")
                        links = soup.find_all("a", href=True)
                        for link in links:
                            href = link['href']
                            if "economictimes.indiatimes.com" in href and "stocks" in href and "companyid" in href:
                                return href
                except Exception as e:
                    print(f"Error searching for URL with {url}: {e}")
        
        return None

    def extract_reports(self, ticker, url=None):
        """
        Extracts brokerage reports/recommendations from the Economic Times page.
        """
        if not url:
            url = self.get_et_url(ticker)
        
        if not url:
            print(f"Could not find Economic Times URL for {ticker}")
            return pd.DataFrame()

        print(f"Fetching data from: {url}")
        try:
            time.sleep(random.uniform(1, 2))
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to fetch page. Status code: {response.status_code}")
                return pd.DataFrame()

            soup = BeautifulSoup(response.content, "html.parser")
            reports = []
            
            # Strategy: Look for the 'Recos' section with id="recos"
            recos_section = soup.find("div", {"id": "recos"})
            
            if recos_section:
                reco_items = recos_section.find_all("div", class_="reco")
                for item in reco_items:
                    try:
                        target = None
                        broker = None
                        reco = None
                        date = None
                        
                        # Parse list items
                        ul = item.find("ul", class_="list")
                        if ul:
                            lis = ul.find_all("li")
                            for li in lis:
                                thead = li.find("span", class_="thead")
                                tval = li.find("span", class_="tval")
                                rtype = li.find("span", class_="rtype")
                                
                                if thead and tval:
                                    label = thead.get_text(strip=True)
                                    value = tval.get_text(strip=True)
                                    if "Target" in label:
                                        target = value
                                    elif "Organization" in label:
                                        broker = value
                                
                                if rtype:
                                    reco = rtype.get_text(strip=True)
                        
                        # Parse date
                        time_elem = item.find("time", class_="date-format")
                        if time_elem:
                            date = time_elem.get("data-time")
                            if not date:
                                date = time_elem.get_text(strip=True)
                        
                        if broker:
                            reports.append({
                                "Date": date,
                                "Broker": broker,
                                "Recommendation": reco,
                                "Target": target
                            })
                    except Exception as e:
                        print(f"Error parsing item: {e}")
                        continue

            df = pd.DataFrame(reports)
            return df

        except Exception as e:
            print(f"Error extracting reports: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    extractor = BrokerageReportExtractor()
    ticker = "SJVN"
    print(f"Extracting reports for {ticker}...")
    
    df = extractor.extract_reports(ticker)
    if not df.empty:
        print(df)
    else:
        print("No reports found.")
