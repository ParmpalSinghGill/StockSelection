import os
import requests
from bs4 import BeautifulSoup
import time
import warnings
import random

# Suppress FutureWarning from google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai

# --- CONFIGURATION ---
TICKER = "Reliance Industries"
DOWNLOAD_FOLDER = "brokerage_reports"
# Get your key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyDy0VY_Ui71Nlm8dBS6FD2FOSq6ocupUsw" 

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

def search_duckduckgo(query, num_results=5):
    """
    Searches DuckDuckGo for the query and returns a list of URLs.
    """
    print(f"🔍 Searching DuckDuckGo for: {query}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://duckduckgo.com/"
    }
    
    # Try multiple endpoints
    endpoints = [
        "https://html.duckduckgo.com/html/",
        "https://lite.duckduckgo.com/lite/"
    ]
    
    found_urls = []
    
    for url in endpoints:
        if len(found_urls) >= num_results:
            break
            
        data = {"q": query}
        try:
            time.sleep(random.uniform(1, 2))
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                links = soup.find_all("a", href=True)
                
                for link in links:
                    href = link['href']
                    
                    # Filter for PDFs if requested in query (simple check)
                    if "filetype:pdf" in query and not href.lower().endswith(".pdf"):
                        # Sometimes DDG returns the PDF link directly, sometimes a redirect.
                        # Let's be lenient but prefer .pdf
                        if "pdf" not in href.lower():
                             continue
                    
                    # Basic filtering to avoid DDG internal links
                    if "duckduckgo.com" not in href and href.startswith("http"):
                        if href not in found_urls:
                            found_urls.append(href)
                            if len(found_urls) >= num_results:
                                break
        except Exception as e:
            print(f"Error searching {url}: {e}")
            
    return found_urls

def find_and_download_reports(ticker, num_results=5):
    """
    Searches for PDF reports and downloads them.
    """
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    print(f"🔍 Searching for '{ticker} brokerage report' PDFs...")
    
    # "filetype:pdf" forces Google to show only PDF files
    query = f"{ticker} brokerage report filetype:pdf after:2024"
    
    downloaded_files = []

    # Search using DuckDuckGo
    urls = search_duckduckgo(query, num_results=num_results)
    
    if not urls:
        print("No URLs found.")
        return []

    for i, url in enumerate(urls):
        try:
            print(f"Found URL: {url}")
            
            # Create a valid filename
            filename = f"{ticker}_report_{i+1}.pdf"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            # Download the file
            response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if response.status_code == 200 and ('application/pdf' in content_type or url.lower().endswith('.pdf')):
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded: {filename}")
                downloaded_files.append(filepath)
            else:
                print(f"❌ Skipped (Not a valid PDF or blocked): {url} (Type: {content_type})")
            
            # Sleep to avoid getting IP blocked by servers
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Error downloading {url}: {e}")

    return downloaded_files

def analyze_with_gemini(pdf_path):
    """
    Uploads the downloaded PDF to Gemini for a summary.
    """
    print(f"\n🤖 Asking Gemini to analyze: {pdf_path}...")
    
    try:
        # 1. Upload the file to Gemini
        sample_file = genai.upload_file(path=pdf_path, display_name="Brokerage Report")
        
        # 2. Wait for processing (usually instant for small PDFs)
        while sample_file.state.name == "PROCESSING":
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)

        # 3. Create the model and prompt
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        You are a senior financial analyst. Read this brokerage report.
        1. What is the Buy/Sell rating?
        2. What is the Target Price?
        3. Summarize the top 3 catalysts for growth mentioned.
        4. List any key risks.
        """
        
        response = model.generate_content([sample_file, prompt])
        
        print("-" * 40)
        print(f"REPORT ANALYSIS FOR: {pdf_path}")
        print("-" * 40)
        print(response.text)
        print("-" * 40)

    except Exception as e:
        print(f"Gemini Analysis Failed: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Step 1: Download
    files = find_and_download_reports(TICKER)
    
    # Step 2: Analyze (Analyze the first successful download as an example)
    if files:
        analyze_with_gemini(files[0])
    else:
        print("No reports could be downloaded. They might be behind paywalls or blocked.")