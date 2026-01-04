import requests
from bs4 import BeautifulSoup

def test_bing():
    query = "Reliance Industries brokerage report filetype:pdf after:2024"
    url = "https://www.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {"q": query}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Bing results are usually in <li class="b_algo"> <h2> <a href="...">
            results = soup.find_all("li", class_="b_algo")
            print(f"Found {len(results)} results.")
            for r in results:
                link = r.find("a", href=True)
                if link:
                    print(f"Link: {link['href']}")
        else:
            print("Bing blocked.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bing()
