import re,json,requests,os,datetime
from bs4 import BeautifulSoup
import pandas as pd

def filterMfFunds():
    df=pd.read_csv("groww_mutual_funds.csv")
    df.pop("Unnamed: 0")
    df=df[df["Rating"]=="5"]
    df=df[df["5Y"]!="--"]
    # print(df.columns)
    # print(df["5Y"].unique())
    df["5Y"]=df["5Y"].map(lambda x:float(x.removesuffix("%")))
    df=df[df["5Y"]>20]
    # print(df["5Y"].unique())
    # print(df.shape)
    # # df=df[d]
    return {row["Fund Name (1,542 results)"]:row["Link"] for i,row in df.iterrows()}


def fetch_holdings(url,mfName):
    Folder=f"MFStocks/{mfName.replace(' ', '_')}"
    outFile = f"{Folder}/{datetime.datetime.now().strftime('%y_%b_%d').upper()}.csv"
    if os.path.exists(outFile):
        print(outFile,"exists continue")
        return
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    # print(soup)c
    div_tag = soup.find('div', id='holdings101Container')
    # print(div_tag)

    holdings = []
    if div_tag:
        table = div_tag.find('table')
        if table:
            tbody = table.find('tbody')
            if tbody:
                for row in tbody.find_all('tr', class_='holdings101Row'):
                    cols = row.find_all('td')
                    if len(cols) == 4:
                        # Name extraction: handle <a> or <div>
                        name_tag = cols[0].find('div', class_='pc543Links')
                        if not name_tag:
                            name_tag = cols[0].find('div')
                        name = name_tag.get_text(strip=True) if name_tag else cols[0].get_text(strip=True)
                        sector = cols[1].get_text(strip=True)
                        instrument = cols[2].get_text(strip=True)
                        assets = cols[3].get_text(strip=True)
                        holdings.append({
                            'scheme': name,
                            'sector': sector,
                            'instrument': instrument,
                            'percentage': assets
                        })
        else:
            raise RuntimeError("Holdings table not found in div_tag")
    else:
        raise RuntimeError("Holdings container div not found")
    os.makedirs(Folder,exist_ok=True)
    pd.DataFrame(holdings).to_csv(outFile,index=None)
    print("Saved at",outFile)
    return holdings



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


if __name__ == "__main__":
    MFDICT.update(filterMfFunds())
    for fund_name,fund_url in MFDICT.items():
        try:
            holdings = fetch_holdings(fund_url,fund_name)
            # print(f"Total holdings fetched: {len(holdings)}")
            # for h in holdings:
            #     print(h)
                # print(f"{h['scheme']:40s} | Qty: {h['quantity']:10} | Value: {h['marketValue']:>10} | %: {h['percentage']}")
        except Exception as e:
            print("Error:", e)
