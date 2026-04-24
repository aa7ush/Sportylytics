import requests
from bs4 import BeautifulSoup
import json

def test_scrape_home():
    url = "https://www.sofascore.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    
    print(f"Fetching: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {r.status_code}, Length: {len(r.text)}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                data = json.loads(script.string)
                # Look for matches data
                # Path is usually: props -> pageProps -> initialSelection -> ... or home -> ...
                print("Found __NEXT_DATA__")
                print(f"Keys: {list(data.get('props', {}).get('pageProps', {}).keys())}")
                
                # Let's save a snippet to analyze
                with open("e:/Sportylytics/scratch/next_data_snippet.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("Saved snippet to scratch/next_data_snippet.json")
            else:
                print("Could not find __NEXT_DATA__")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scrape_home()
