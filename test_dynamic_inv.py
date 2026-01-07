import requests
import random

VIDEO_ID = "Hu4Yvq-g7_Y"

def get_working_invidious_instance():
    try:
        print("Fetching instances list...")
        # Get list of instances that support API
        resp = requests.get("https://api.invidious.io/instances.json?sort_by=health", timeout=5)
        data = resp.json()
        
        # Filter: type=https, api=true
        candidates = []
        for domain, details in data:
            if details.get("type") == "https" and details.get("api") == True:
                candidates.append(details["uri"])
        
        print(f"Found {len(candidates)} candidates.")
        # Shuffle to load balance
        random.shuffle(candidates)
        
        # Try top 5
        for uri in candidates[:5]:
            print(f"Trying {uri}...")
            try:
                # Check video existence
                v_url = f"{uri}/api/v1/videos/{VIDEO_ID}"
                r = requests.get(v_url, timeout=5)
                if r.status_code == 200:
                    print(f"FOUND WORKING INSTANCE: {uri}")
                    return uri
            except:
                pass
    except Exception as e:
        print(f"Error fetching instances: {e}")
    return None

def test_dynamic_invidious():
    instance = get_working_invidious_instance()
    if not instance:
        print("No working instance found.")
        return

    # Try fetch captions
    try:
        url = f"{instance}/api/v1/videos/{VIDEO_ID}"
        data = requests.get(url).json()
        captions = data.get("captions", [])
        
        en_cap = next((c for c in captions if c["language"] == "en"), None)
        if en_cap:
            print(f"Fetching caption from {instance}{en_cap['url']}")
            r2 = requests.get(f"{instance}{en_cap['url']}")
            print(f"Status: {r2.status_code}")
            print(f"Snippet: {r2.text[:200]}")
        else:
            print("No English captions on this instance.")
            
    except Exception as e:
        print(f"Error fetching caption: {e}")

test_dynamic_invidious()
