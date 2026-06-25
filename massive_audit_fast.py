import urllib.request
import json
import subprocess
import os
import sys
import time

BASE_URL = 'http://127.0.0.1:8000'
OUTPUT_FILE = r'C:\Users\User\.gemini\antigravity\brain\10debabb-94ac-4a29-8112-46e6c40571b2\massive_audit_results.md'
TEMP_JSON = 'temp_report.json'

def get_urls():
    try:
        with urllib.request.urlopen(f'{BASE_URL}/api/tools/catalog') as response:
            data = json.loads(response.read().decode())
            urls = ['/'] + [t['url'] for t in data]
            return urls
    except Exception as e:
        print(f"Error fetching catalog: {e}")
        return []

def run_lighthouse(url_path):
    full_url = f'{BASE_URL}{url_path}'
    cmd = f'cmd.exe /c "npx -y lighthouse {full_url} --output json --output-path {TEMP_JSON} --chrome-flags=\"--headless\""'
    print(f'Auditing {url_path}...', flush=True)
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    try:
        if not os.path.exists(TEMP_JSON):
            return None
        with open(TEMP_JSON, 'r', encoding='utf-8') as f:
            d = json.load(f)
        cats = d.get('categories', {})
        
        perf = int(cats.get('performance', {}).get('score', 0) * 100)
        acc = int(cats.get('accessibility', {}).get('score', 0) * 100)
        bp = int(cats.get('best-practices', {}).get('score', 0) * 100)
        seo = int(cats.get('seo', {}).get('score', 0) * 100)
        agent = int(cats.get('agentic-browsing', {}).get('score', 0) * 100)
        
        os.remove(TEMP_JSON)
        return perf, acc, bp, seo, agent
    except Exception as e:
        print(f"Error reading report for {url_path}: {e}")
        return None

def main():
    urls = get_urls()
    print(f"Starting massive audit for {len(urls)} URLs...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Massive 77-Page Lighthouse Audit Results\n\n")
        f.write("This table shows the real-time Lighthouse scores for every single page on the application. A score of 100 indicates absolute perfection according to Google's strictest metrics.\n\n")
        f.write("| Path | Performance | Accessibility | Best Practices | SEO | Agentic Browsing |\n")
        f.write("|---|---|---|---|---|---|\n")
        
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Auditing {url}", flush=True)
        res = run_lighthouse(url)
        if res:
            perf, acc, bp, seo, agent = res
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"| `{url}` | {perf} | {acc} | {bp} | {seo} | {agent} |\n")
        time.sleep(1) # Prevent Chrome thrashing
                
    print("Massive audit complete!", flush=True)

if __name__ == '__main__':
    main()
