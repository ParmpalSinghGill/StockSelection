from operator import le
import re,json,requests,os,datetime,time
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

overright_exisisting_files=True

def ETFScrapper(url = "https://groww.in/etfs/bharat-etf-icici-prudential-amc"):
    # print("ETFScrapper",url)
    # Setup headless browser
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    # Open the page
    driver.get(url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "ehr887TablePeer")))

    all_rows = []
    processed=1
    while True:
        time.sleep(2)
        table = driver.find_element(By.ID, "ehr887TablePeer")
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                company = cols[0].text.strip()
                asset_pct = cols[1].text.strip()
                sector = cols[3].text.strip()
                url_element = cols[0].find_element(By.CLASS_NAME, 'pr54companyName')
                url = url_element.get_attribute('href')
                all_rows.append({
                            'scheme': company,'sector': sector,
                            'instrument': "Equity",'percentage': asset_pct,
                            'URL': url,'Type': "Stock"
                        })
        # print(f"Number of row {len(rows)} stocks {len(all_rows)}")
        # Try clicking the custom "Next" button
        try:
            pg1231Container=table.find_element(By.CLASS_NAME, "pg1231Container")
            next_btns=pg1231Container.find_elements(By.CLASS_NAME, "pg1231Box")[processed:]
            if len(next_btns)==0: break
            if next_btns[0].is_displayed():
                # print(f"next button clicked {processed} times")
                next_btns[0].click()
            else:
                break
            processed+=1
        except Exception as e:
            print(f"Exception in next button pressing {e} in page {processed}")
            break

    driver.quit()

    return all_rows




def filterMfFunds():
    print(os.getcwd())
    df=pd.read_csv("../groww_mutual_funds.csv")
    df.pop("Unnamed: 0")
    df=df[df["Rating"].isin(["3","4","5"])]
    df=df[df["5Y"]!="--"]
    # print(df.columns)
    # print(df["5Y"].unique())
    df["5Y"]=df["5Y"].map(lambda x:float(x.removesuffix("%")))
    df=df[df["5Y"]>20]
    # print(df["5Y"].unique())
    # print(df.shape)
    # # df=df[d]
    print(df.columns)
    columnname="Fund Name (1,559 results)"
    return {row[columnname]:row["Link"] for i,row in df.iterrows()}



def fetch_mtf_holdings(url,mfName):
    # print(f"Fetching for {url} mfname {mfName}")
    Folder=f"MFStocks/{mfName.replace(' ', '_')}"
    outFile = f"{Folder}/{datetime.datetime.now().strftime('%y_%b_%d').upper()}.csv"
    # outFile = f"{Folder}/{(datetime.datetime.now()-datetime.timedelta(days=1)).strftime('%y_%b_%d').upper()}.csv"
    if not overright_exisisting_files and os.path.exists(outFile):
        print(outFile,"exists continue")
        return [row.to_dict() for i,row in pd.read_csv(outFile).iterrows()]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=10)

    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    # print(soup)
    div_tag = soup.find('div', id='holdings101Container')
    # print(div_tag)

    holdings = []
    if div_tag:
        table = div_tag.find('table')
        if table:
            tbody = table.find('tbody')
            if tbody:
                for row in tbody.find_all('tr', class_='holdings101Row'):
                    surl=url
                    cols = row.find_all('td')
                    if len(cols) == 4:
                        try:
                            # Name extraction: handle <a> or <div>
                            name_tag = cols[0].find('div', class_='pc543Links')
                            if not name_tag:
                                name_tag = cols[0].find('div')
                            name = name_tag.get_text(strip=True) if name_tag else cols[0].get_text(strip=True)
                            if "ETF" in name:
                                etfname=cols[0].find('a', class_='cur-po').get('href').removeprefix("/stocks")
                                surl=surl.split("mutual-funds")[0]+"etfs"+etfname
                                Type="ETF"
                            else:
                                if cols[0].find('a', class_='cur-po') is not None:
                                    sname=cols[0].find('a', class_='cur-po').get('href')
                                    surl=surl.split("mutual-funds")[0]+sname
                                else:
                                    surl=None
                                Type="Stock"
                            sector = cols[1].get_text(strip=True)
                            instrument = cols[2].get_text(strip=True)
                            assets = cols[3].get_text(strip=True)
                            holdings.append({
                                'scheme': name,
                                'sector': sector,
                                'instrument': instrument,
                                'percentage': assets,
                                'URL': surl,
                                'Type': Type
                            })
                        except Exception as e:
                            print(f"Exception {e} in {cols}")
        else:
            raise RuntimeError("Holdings table not found in div_tag")
    else:
        raise RuntimeError("Holdings container div not found")

    stockHoldings=[]
    for holding in holdings:
        if holding["Type"] =="ETF":
            try:
                stockHoldings.extend(ETFScrapper(holding["URL"]))
            except:
                pass
        if holding["Type"] =="Stock":
            stockHoldings.append(holding)

    os.makedirs(Folder,exist_ok=True)
    pd.DataFrame(stockHoldings).to_csv(outFile,index=None)
    print("Saved at",outFile)
    return stockHoldings

# def fetch_etf_holdings(url,mfName):



MFDICT={"Motilal Oswal Midcap Fund Direct Growth":"https://groww.in/mutual-funds/motilal-oswal-most-focused-midcap-30-fund-direct-growth",
        "HDFC BSE Sensex Index Fund Direct Growth":"https://groww.in/mutual-funds/hdfc-bse-sensex-index-fund-direct-growth",
        "Tata Digital India Fund Direct Growth":"https://groww.in/mutual-funds/tata-digital-india-fund-direct-growth",
        "Motilal Oswal Nifty India Defence Index Fund Direct Growth":"https://groww.in/mutual-funds/motilal-oswal-nifty-india-defence-index-fund-direct-growth",
        "HDFC Balanced Advantage Fund Direct Growth":"https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
        "Nippon India Small Cap Fund Direct Growth":"https://groww.in/mutual-funds/nippon-india-small-cap-fund-direct-growth",
        "Motilal Oswal Flexi Cap Fund Direct Growth":"https://groww.in/mutual-funds/motilal-oswal-most-focused-multicap-35-fund-direct-growth",
        "Motilal Oswal Large and Midcap Fund Direct Growth":"https://groww.in/mutual-funds/motilal-oswal-large-and-midcap-fund-direct-growth",
        "SBI Flexicap Fund Direct Growth":"https://groww.in/mutual-funds/sbi-flexicap-fund-direct-growth",
        "Invesco India PSU Equity Fund Direct Growth":"https://groww.in/mutual-funds/invesco-india-psu-equity-fund-direct-growth",
        "SBI PSU Direct Plan Growth":"https://groww.in/mutual-funds/invesco-india-psu-equity-fund-direct-growth",
        "Nippon India Power & Infra Fund Direct Growth":"https://groww.in/mutual-funds/nippon-india-power-infra-fund-direct-growth",
        "Aditya Birla Sun Life PSU Equity Fund Direct Growth":"https://groww.in/mutual-funds/aditya-birla-sun-life-psu-equity-fund-direct-growth",
        "ICICI Prudential Infrastructure Direct Growth":"https://groww.in/mutual-funds/icici-prudential-infrastructure-fund-direct-growth",
        "LIC MF Infrastructure Fund Direct Growth":"https://groww.in/mutual-funds/lic-mf-infrastructure-fund-direct-growth",
        "Canara Robeco Infrastructure Direct Growth":"https://groww.in/mutual-funds/canara-robeco-infrastructure-fund-direct-growth",
        "DSP India T.I.G.E.RMFDICT. (The Infrastructure Growth and Economic Reforms Fund) Direct Growth":"https://groww.in/mutual-funds/dsp-india-t.i.g.e.r.-(the-infrastructure-growth-and-economic-reforms-fund)-direct-growth",
        "ICICI Prudential BHARAT 22 FOF Direct Growth":"https://groww.in/mutual-funds/icici-prudential-bharat-22-fof-direct-growth",
        "Parag Parikh Flexi Cap Fund Direct Growth":"https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth",
        "Bandhan Small Cap Fund Direct Growth":"https://groww.in/mutual-funds/bandhan-small-cap-fund-direct-growth",
        "HDFC Flexi Cap Direct Plan Growth":"https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"
        }

# def fetch


if __name__ == "__main__":
    MFDICT.update(filterMfFunds())
    # fund_name="Motilal_Oswal_Nifty_India_Defence_Index_Fund_Direct_Growth"
    # fund_name="Motilal_Oswal_Flexi_Cap_Fund_Direct_Growth"
    # fund_name="Motilal_Oswal_Large_and_Midcap_Fund_Direct_Growth"
    # fund_name="Invesco_India_PSU_Equity_Fund_Direct_Growth"
    # fund_name="SBI_PSU_Direct_Plan_Growth"
    # fund_name="Aditya_Birla_Sun_Life_PSU_Equity_Fund_Direct_Growth"
    # fund_name="ICICI_Prudential_BHARAT_22_FOF_Direct_Growth"
    # fund_name="HDFC_Flexi_Cap_Fund"
    # # fund_name="Motilal_Oswal_Large_and_Midcap_Fund"
    # # fund_name="ICICI_Prudential_BHARAT_22_FOF_Fund"
    # fund_name=fund_name.replace("_"," ")
    # fund_url=MFDICT[fund_name]
    # holdings = fetch_mtf_holdings(fund_url,fund_name)
    # for h in holdings:
    #     print(h)
    # print(len(holdings))
    for fund_name,fund_url in MFDICT.items():
        # try:
        holdings = fetch_mtf_holdings(fund_url,fund_name)
        print(f"Total holdings fetched: {fund_name} : {len(holdings)}")
    #     for h in holdings:
    #         # print(h)
    #         print(f"{h['scheme']:40s} |  %: {h['percentage']}")
    #     except Exception as e:
    #         print("Error:", e)
