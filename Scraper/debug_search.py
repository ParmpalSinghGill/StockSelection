from googlesearch import search

def test_search():
    query = "Reliance Industries brokerage report filetype:pdf after:2024"
    print(f"Testing query: {query}")
    try:
        results = search(query, num_results=5, advanced=True)
        count = 0
        for r in results:
            print(f"Result: {r.url}")
            count += 1
        print(f"Total results: {count}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
