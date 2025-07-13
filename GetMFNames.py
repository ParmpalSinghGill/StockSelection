from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time

# Set up Chrome options
options = Options()
# options.add_argument("--headless")  # Uncomment if you want headless
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver
driver = webdriver.Chrome(options=options)

# Target URL
url = "https://groww.in/screener/mutual-funds"
driver.get(url)

# Wait for the page to load JS data
time.sleep(2)

# Locate the table element
table_header = driver.find_element(By.XPATH, '//thead')
# Extract table headers
headers = [th.text for th in table_header.find_elements(By.TAG_NAME, "th")]
headers.insert(2, "Link")

# Scroll inside the container to load all rows
scrollable_div = driver.find_element(By.ID, "scrollableDiv")
prev_count = -1
while True:
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
    time.sleep(1.2)
    rows_now = driver.find_elements(By.XPATH, '//table//tbody/tr')
    if len(rows_now) == prev_count:
        break
    prev_count = len(rows_now)
    print(f"Scrolled: {prev_count} rows loaded")



table_element = driver.find_element(By.XPATH, '//table')
rows = []
for tr in table_element.find_elements(By.TAG_NAME, "tr")[1:]:  # skip header
    tds = tr.find_elements(By.TAG_NAME, "td")
    row_data = []
    for i, td in enumerate(tds):
        text = td.text.strip()
        if i == 1:  # Fund Name column
            try:
                a_tag = td.find_element(By.TAG_NAME, "a")
                link = a_tag.get_attribute("href")
            except:
                link = ""
            row_data.append(text)
            row_data.append("https://groww.in" + link if link.startswith("/") else link)
        else:
            row_data.append(text)
    rows.append(row_data)

# Convert to DataFrame
df = pd.DataFrame(rows, columns=headers)
print(f"\n✅ Scraped {len(df)} mutual fund entries from {url}")
print(df.head())

# Save to CSV
df.to_csv("groww_mutual_funds.csv", index=False)

# Close browser
driver.quit()
