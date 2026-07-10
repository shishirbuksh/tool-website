import urllib.request
import re

url = "https://www.storybrainai.com/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    scripts = re.findall(r'<script[^>]+src=[\"\']([^\"\']+)[\"\']', html)
    print("Found scripts:", scripts)
    for s in scripts:
        try:
            full_url = "https://www.storybrainai.com" + s if s.startswith('/') else s
            req_s = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req_s)
            print(f"{s}: {res.getcode()}")
        except urllib.error.HTTPError as e:
            print(f"{s}: ERROR {e.code}")
        except Exception as e:
            print(f"{s}: ERROR {e}")
            
    # Also test sw.js manually
    try:
        sw_req = urllib.request.Request("https://www.storybrainai.com/sw.js", headers={'User-Agent': 'Mozilla/5.0'})
        sw_res = urllib.request.urlopen(sw_req)
        print(f"/sw.js: {sw_res.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"/sw.js: ERROR {e.code}")
        
    try:
        sw_req2 = urllib.request.Request("https://www.storybrainai.com/sw.js?v=2", headers={'User-Agent': 'Mozilla/5.0'})
        sw_res2 = urllib.request.urlopen(sw_req2)
        print(f"/sw.js?v=2: {sw_res2.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"/sw.js?v=2: ERROR {e.code}")
        
except Exception as e:
    print(f"Failed to fetch {url}: {e}")
