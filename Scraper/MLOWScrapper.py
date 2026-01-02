#!/usr/bin/env python3
"""
Selenium crawler + downloader for Excel files on a JS-heavy site.
Example start URL: https://www.motilaloswalmf.com/download/scheme-portfolio-details
"""

import os,wget
import re
import time
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------- CONFIG --------
START_URL = "https://www.motilaloswalmf.com/download/scheme-portfolio-details"
OUT_DIR = "downloads"
ALLOWED_EXT = (".xls", ".xlsx", ".csv", ".xlsm")
WORKERS = 6
MAX_PAGES = 150          # max pages to render/crawl
PAGE_WAIT = 3            # seconds to wait after page load (for lazy JS)
HEADLESS = False
# ------------------------

os.makedirs(OUT_DIR, exist_ok=True)
parsed_start = urlparse(START_URL)
DOMAIN = parsed_start.netloc

def sanitize_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*\n\r]+', "_", s).strip()

def looks_like_spreadsheet(url: str) -> bool:
    if not url:
        return False
    u = url.split("?", 1)[0].lower()
    return any(u.endswith(ext) for ext in ALLOWED_EXT) or "/uploads/" in u and "." in os.path.basename(u)

def is_same_domain(url: str) -> bool:
    try:
        p = urlparse(url)
        return (p.netloc == "" or p.netloc == DOMAIN)
    except:
        return False

def make_driver():
    chrome_opts = Options()
    if HEADLESS:
        chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-notifications")
    chrome_opts.add_argument("--disable-popup-blocking")
    chrome_opts.add_argument("--disable-geolocation")
    # set a realistic user-agent
    chrome_opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    
    # Stealth settings
    chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_opts)
    driver.set_page_load_timeout(40)
    return driver

def collect_links_from_page(driver, base_url):
    """Return set of absolute links (href/src) found after rendering page."""
    links = set()
    # look for anchors
    elems = driver.find_elements(By.XPATH, "//a[@href]")
    for e in elems:
        try:
            href = e.get_attribute("href")
            if href:
                links.add(href)
        except:
            pass
    # also images/script srcs (rare)
    elems2 = driver.find_elements(By.XPATH, "//*[@src]")
    for e in elems2:
        try:
            src = e.get_attribute("src")
            if src:
                links.add(src)
        except:
            pass
    # normalize relative -> absolute via urljoin
    normalized = set(urljoin(base_url, l) for l in links)
    return normalized

def crawl_with_selenium(start_url, max_pages=MAX_PAGES):
    driver = make_driver()
    url = start_url
    seen = set()
    files = set()
    pages = 0
    os.makedirs("MFFunds", exist_ok=True)
    downloaded_files=[]
    scrapped_pages=2
    try:
        print(f"[CRAWL] Rendering: {url}")
        try:
            driver.get(url)
        except Exception as e:
            print(f"  [WARN] load failed: {e} -- continuing")
        # small wait for JS-driven content to appear
        time.sleep(PAGE_WAIT)
        # wait for input            
        try:
            inp = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "schameName")))
        except Exception as e:
            print(f"[ERR] Timeout waiting for schameName. Saving source to debug_source.html")
            with open("debug_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise e
        inp.clear()
        inp.send_keys("End")
        # try waiting for at least one <a> to appear (if none, continue)
        while True:
            time.sleep(5)
            try:
                wait = WebDriverWait(driver, 10)
                next_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "ul.pagination.justify-content-end.mb-3 a[rel='next']"
                )))
                # WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "pagination justify-content-end mb-3")))
            except Exception as e:
                print(f"[ERR] Timeout waiting for next button: {e}")
            seen.add(url)
            pages += 1
            if pages<=scrapped_pages:
                print("Page ", pages, " already scrapped")
                next_button.click()                
                continue
            try:
                container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "downloadWithPagination_downloadContainer__lO6rx"))
                )
                print("[DEBUG] Found download container")
                
                # Get all children (direct descendants)
                children = container.find_elements(By.XPATH, "./*")
                print(f"[DEBUG] Found {len(children)} children in container")

                for child in children:
                    # Look for links within the child
                    child_ele = child.find_element(By.TAG_NAME, "img")
                    print(f"[DEBUG] Found {child_ele} elements in child")
                    
                    # Scroll element into center of view to avoid sticky headers
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", child_ele)
                    time.sleep(0.5) # Small wait for scroll to finish
                    
                    try:
                        child_ele.click()
                    except Exception:
                        # Fallback to JS click if standard click still fails
                        driver.execute_script("arguments[0].click();", child_ele)
                        
                    time.sleep(1)
                    child_links = child.find_elements(By.TAG_NAME, "a")
                    for link in child_links:
                        hlink=link.get_attribute('href')
                        if hlink.startswith("https://www.motilaloswalmf.com"):
                            if hlink not in downloaded_files:
                                print("Downloading file: ", hlink)
                                wget.download(hlink, out="MFFunds/")
                                downloaded_files.append(hlink)
                            break
            except Exception as e:
                print(f"[ERR] Failed to process download container: {e}")

            is_disabled = next_button.get_attribute("aria-disabled")
            if is_disabled == "true":
                print("Next button is disabled")
                break
            else:
                print("Next button is enabled")
                next_button.click()

        # fetch cookies & headers for requests session
        selenium_cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent;")
    finally:
        driver.quit()

    print(f"[CRAWL] done. pages rendered: {pages}, spreadsheet links found: {len(files)}")
    return sorted(files), selenium_cookies, user_agent

def cookies_to_requests_session(cookies, user_agent=None):
    s = requests.Session()
    headers = {"User-Agent": user_agent} if user_agent else {}
    s.headers.update(headers)
    for c in cookies:
        s.cookies.set(c['name'], c.get('value', ''), domain=c.get('domain'))
    return s

def download_file(session, url):
    try:
        resp = session.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        # try content-disposition filename
        fname = None
        cd = resp.headers.get("content-disposition", "")
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
        if m:
            fname = m.group(1)
        else:
            fname = os.path.basename(urlparse(url).path) or f"download_{int(time.time())}"
        fname = sanitize_filename(fname)
        outpath = os.path.join(OUT_DIR, fname)
        base, ext = os.path.splitext(outpath)
        i = 1
        while os.path.exists(outpath):
            outpath = f"{base}__{i}{ext}"
            i += 1
        with open(outpath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024*32):
                if chunk:
                    f.write(chunk)
        print(f"[OK] {url} -> {outpath}")
        return outpath
    except Exception as e:
        print(f"[ERR] {url} -> {e}")
        return None

def main():
    print("Starting Selenium crawl (may take a minute)...")
    files, cookies, ua = crawl_with_selenium(START_URL)
    if not files:
        print("No spreadsheet links found. You can raise PAGE_WAIT, MAX_PAGES or disable HEADLESS to debug.")
        return
    # print("Creating requests session with browser cookies to download files...")
    # sess = cookies_to_requests_session(cookies, user_agent=ua)
    # # parallel download
    # with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    #     futures = {ex.submit(download_file, sess, url): url for url in files}
    #     for fut in as_completed(futures):
    #         _ = fut.result()

if __name__ == "__main__":
    main()
