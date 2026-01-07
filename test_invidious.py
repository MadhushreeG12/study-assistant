import requests

VIDEO_ID = "Hu4Yvq-g7_Y" # The known working video
# List of instances to try
INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://invidious.projectsegfau.lt",
    "https://invidious.fdn.fr"
]

def test_invidious():
    for instance in INSTANCES:
        print(f"Testing {instance}...")
        try:
            # Get video info to find caption tracks
            url = f"{instance}/api/v1/videos/{VIDEO_ID}"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                print(f"Failed to get video info: {res.status_code}")
                continue
            
            data = res.json()
            captions = data.get("captions", [])
            print(f"Found {len(captions)} caption tracks.")
            
            # Find English
            en_cap = next((c for c in captions if c["language"] == "en"), None)
            if en_cap:
                print(f"Found English caption: {en_cap['label']}")
                # Fetch it
                cap_url = f"{instance}{en_cap['url']}"
                print(f"Fetching caption from {cap_url}")
                r2 = requests.get(cap_url)
                if r2.status_code == 200:
                    print(f"SUCCESS! Retrieved captions via {instance}")
                    print(f"Snippet: {r2.text[:100]}...")
                    return
            else:
                print("No English captions found on this instance.")
                
        except Exception as e:
            print(f"Error checking {instance}: {e}")

test_invidious()
