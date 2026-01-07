import requests
import re
import json

VIDEO_ID = "Hu4Yvq-g7_Y"

def test_manual_extraction():
    url = f"https://www.youtube.com/watch?v={VIDEO_ID}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers)
        html = resp.text
        
        # Look for "captions" json in the player response
        # It's usually inside ytInitialPlayerResponse
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
        if not match:
            # Try searching for the json directly if the variable name changed
            match = re.search(r'playerParams"\s*:\s*".+?","captions"\s*:\s*({.+?})', html)
        
        if match:
            print("Found player response JSON candidate.")
            try:
                data = json.loads(match.group(1))
                # extracting captions logic
                captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
                
                if captions:
                    print(f"Found {len(captions)} caption tracks.")
                    first = captions[0]
                    print(f"Track: {first['name']['simpleText']} - {first['languageCode']}")
                    print(f"URL: {first['baseUrl']}")
                    
                    # fetch xml/fmt3
                    c_res = requests.get(first['baseUrl'])
                    print(f"Caption fetch status: {c_res.status_code}")
                    print(f"Caption content size: {len(c_res.text)}")
                    if c_res.status_code == 200:
                         print(c_res.text[:200])
                    return
            except:
                pass
                
        print("Could not extract captions from HTML.")
        # Debug: check if we got a "Sign in" page
        if "Sign in" in html:
            print("Detected 'Sign in' prompt in HTML.")

    except Exception as e:
        print(f"Error: {e}")

test_manual_extraction()
