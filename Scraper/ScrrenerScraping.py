import requests
from bs4 import BeautifulSoup
import pandas as pd
import json

class ScreenerScraper:
    def __init__(self, ticker):
        self.ticker = ticker
        self.url = f"https://www.screener.in/company/{ticker}/"
        self.soup = None

    def fetch_data(self):
        try:
            response = requests.get(self.url)
            if response.status_code == 200:
                self.soup = BeautifulSoup(response.content, "html.parser")
                return True
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False

    def get_top_ratios(self):
        ratios = {}
        if not self.soup:
            return ratios
        
        top_ratios = self.soup.find("ul", {"id": "top-ratios"})
        if top_ratios:
            for li in top_ratios.find_all("li"):
                name_span = li.find("span", {"class": "name"})
                value_span = li.find("span", {"class": "value"})
                if name_span and value_span:
                    name = name_span.text.strip()
                    value = value_span.text.strip()
                    # Clean value
                    value = value.replace('₹', '').replace('Cr.', '').replace('%', '').strip()
                    try:
                        value = float(value.replace(',', ''))
                    except ValueError:
                        pass
                    ratios[name] = value
        return ratios

    def get_table_data(self, section_id):
        if not self.soup:
            return None
        
        section = self.soup.find("section", {"id": section_id})
        if not section:
            return None
        
        table = section.find("table")
        if not table:
            return None

        # Parse table headers
        headers = []
        thead = table.find("thead")
        if thead:
            headers = [th.text.strip() for th in thead.find_all("th")]
        
        # Parse rows
        data = {}
        tbody = table.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                if not tds:
                    continue
                row_name = tds[0].text.strip()
                row_values = []
                for td in tds[1:]:
                    val = td.text.strip().replace(',', '').replace('%', '')
                    try:
                        val = float(val)
                    except ValueError:
                        val = 0.0 # or None
                    row_values.append(val)
                
                data[row_name] = row_values
            
        # Create DataFrame
        # headers[0] is usually empty or 'Year'
        cols = headers[1:] if len(headers) > 1 else []
        
        # Handle case where columns might not match data length exactly (though usually they do in screener)
        # We will just return the dictionary mapped to columns if possible, or just the raw dict
        
        if cols:
             # Ensure data lists match cols length
             cleaned_data = {}
             for k, v in data.items():
                 if len(v) == len(cols):
                     cleaned_data[k] = dict(zip(cols, v))
                 else:
                     # Fallback if lengths mismatch
                     cleaned_data[k] = v
             return cleaned_data
        
        return data

    def scrape(self):
        if not self.fetch_data():
            return None

        data = {}
        
        # 1. Top Ratios
        ratios = self.get_top_ratios()
        data['Current Price'] = ratios.get('Current Price')
        data['Market Cap'] = ratios.get('Market Cap')
        data['PE'] = ratios.get('Stock P/E')
        data['ROCE'] = ratios.get('ROCE')
        data['ROE'] = ratios.get('ROE')
        data['Book Value'] = ratios.get('Book Value')
        
        # Calculate PB if possible
        if data.get('Current Price') and data.get('Book Value'):
            data['PB'] = round(data['Current Price'] / data['Book Value'], 2)
        
        # 2. Profit & Loss
        pl_data = self.get_table_data("profit-loss")
        if pl_data:
            # Get last few periods
            data['Operating Profit'] = pl_data.get('Operating Profit', {})
            # Handle potential variations in key names
            for k in pl_data.keys():
                if 'Net Profit' in k:
                    data['Net Profit'] = pl_data[k]
                if 'EPS' in k:
                    data['EPS'] = pl_data[k]

        # 3. Shareholding
        sh_data = self.get_table_data("shareholding")
        if sh_data:
             for k in sh_data.keys():
                 if 'Promoters' in k:
                     data['Promoter Holding'] = sh_data[k]
                 elif 'FIIs' in k:
                     data['FII Holding'] = sh_data[k]
                 elif 'DIIs' in k:
                     data['DII Holding'] = sh_data[k]

        # 4. Balance Sheet for Debt to Equity
        bs_data = self.get_table_data("balance-sheet")
        if bs_data:
             borrowings = {}
             share_capital = {}
             reserves = {}
             
             for k in bs_data.keys():
                 if 'Borrowings' in k:
                     borrowings = bs_data[k]
                 elif 'Equity Capital' in k or 'Share Capital' in k:
                     share_capital = bs_data[k]
                 elif 'Reserves' in k:
                     reserves = bs_data[k]
             
             # Calculate Debt to Equity for the latest year
             if borrowings and share_capital and reserves:
                 years = sorted(list(set(borrowings.keys()) & set(share_capital.keys()) & set(reserves.keys())))
                 if years:
                     latest_year = years[-1]
                     debt = borrowings.get(latest_year, 0)
                     equity = share_capital.get(latest_year, 0) + reserves.get(latest_year, 0)
                     if equity != 0:
                         data['Debt to Equity'] = round(debt / equity, 2)
                     else:
                         data['Debt to Equity'] = None

        return data

if __name__ == "__main__":
    scraper = ScreenerScraper("WEBELSOLAR")
    result = scraper.scrape()
    print(json.dumps(result, indent=4))
