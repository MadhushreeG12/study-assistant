import requests
import re
import json
import http.cookiejar
import os

VIDEO_ID = "Hu4Yvq-g7_Y"

def load_cookies(session, filename):
    if not os.path.exists(filename):
        print("No cookies.txt found.")
        return
    try:
        cj = http.cookiejar.MozillaCookieJar(filename)
        cj.load(ignore_discard=True, ignore_expires=True)
        session.cookies = cj
        print(f"Loaded cookies from {filename}")
    except Exception as e:
        print(f"Error loading cookies: {e}")

def test_manual_with_cookies():
    session = requests.Session()
    # Headers to mimic a real browser
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    })
    
    load_cookies(session, "cookies.txt")
    
    url = f"https://www.youtube.com/watch?v={VIDEO_ID}"
    print(f"Fetching {url}...")
    
    try:
        resp = session.get(url)
        html = resp.text
        
        # Check for Sign in/Consent
        if "Consent to the use of cookies" in html or "Before you continue" in html:
             print("Hit Cookie Consent Wall.")
        
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
        if not match:
             match = re.search(r'var\s+ytInitialPlayerResponse\s*=\s*({.+?});', html)
             
        if match:
            print("Found player JSON.")
            data = json.loads(match.group(1))
            captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
            
            if captions:
                print(f"Found {len(captions)} tracks.")
                first = captions[0]
                print(f"Trying to fetch: {first['baseUrl']}")
                
                # Fetch content
                c_resp = session.get(first['baseUrl'])
                print(f"Status: {c_resp.status_code}")
                print(f"Size: {len(c_resp.text)}")
                if len(c_resp.text) > 100:
                    print("SUCCESS! Content found.")
                    print(c_resp.text[:100])
                else:
                    print("EMPTY CONTENT.")
            else:
                print("No caption tracks in JSON.")
        else:
            print("No player JSON found.")

    except Exception as e:
        print(f"Error: {e}")

test_manual_with_cookies()
