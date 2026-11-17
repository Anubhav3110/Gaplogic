import json
import logging
import requests
import os
import datetime
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from tavily import TavilyClient

# Setup directories
os.makedirs('sessions', exist_ok=True)
SESSION_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = f"sessions/{SESSION_ID}"
os.makedirs(SESSION_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, filename=f'{SESSION_DIR}/marketwar.log', format='%(asctime)s - %(message)s')

def get_website_text(url, limit=6000):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])])
        return text[:limit]
    except Exception as e:
        return f"Error reading website {url}: {e}"

def clean_json(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()

def run_market_conqueror():
    with open('config.json', 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
    
    client = OpenAI(base_url=config['api_base'], api_key=config['api_key'])
    tavily = TavilyClient(api_key=config['tavily_api_key'])
    
    report_path = f"{SESSION_DIR}/GAPLOGIC_REPORT.md"
    
    print(f"🚀 --- GapLogic v2.0 Started: {SESSION_ID} ---")
    
    # PHASE 1: Baseline the Client
    print(f"Phase 1: Analyzing Your Company Baseline ({config['client_url']})...")
    client_content = get_website_text(config['client_url'])
    baseline_prompt = f"""
    Analyze the following website content for our client company. 
    Target Audience: {config['target_audience']}
    Website Content: {client_content}
    
    Identify:
    1. Core unique selling points (USPs).
    2. Brand personality.
    3. Current market positioning.
    
    Return a professional summary.
    """
    baseline_resp = client.chat.completions.create(
        model=config['model'],
        messages=[{"role": "user", "content": baseline_prompt}]
    )
    client_profile = baseline_resp.choices[0].message.content
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# GAPLOGIC: STRATEGIC OVERTAKE REPORT\n\n")
        f.write(f"## Client Baseline\n\n{client_profile}\n\n")

    # PHASE 2: Discovery (Find 100)
    print(f"Phase 2: Searching for up to 100 competitors...")
    search_query = config.get('search_query', f"competitors for {config['client_url']} targeting {config['target_audience']}")
    search_results = tavily.search(query=search_query, search_depth="advanced", max_results=100)
    
    discovered_urls = [r['url'] for r in search_results['results'] if config['client_url'] not in r['url']]
    print(f"Found {len(discovered_urls)} potential sites.")

    # PHASE 3: Light Scan & Ranking
    print(f"Phase 3: Light-scanning {len(discovered_urls)} sites to find the Top 5 Threats...")
    all_scores = []
    
    for idx, url in enumerate(discovered_urls):
        print(f"[{idx+1}/{len(discovered_urls)}] Screening: {url}")
        summary = get_website_text(url, limit=1200) # Fast screen
        
        eval_prompt = f"""
        Quickly evaluate if this company is a DIRECT competitor to our client for the target audience.
        Target Audience: {config['target_audience']}
        Competitor Summary: {summary}
        
        Return ONLY a JSON object: {{ "name": "Name", "score": 1-10, "is_direct": true/false }}
        """
        try:
            eval_resp = client.chat.completions.create(
                model=config['model'],
                messages=[{"role": "user", "content": eval_prompt}],
                response_format={ "type": "json_object" }
            )
            data = json.loads(clean_json(eval_resp.choices[0].message.content))
            if data.get('is_direct'):
                all_scores.append({ "url": url, "name": data['name'], "score": data['score'] })
        except:
            continue

    # Pick Top 5
    top_5 = sorted(all_scores, key=lambda x: x['score'], reverse=True)[:5]
    
    with open(report_path, 'a', encoding='utf-8') as f:
        f.write(f"## Market Landscape\nScanned {len(discovered_urls)} potential competitors. Identified the following Top 5 Strategic Threats:\n\n")
        for i, c in enumerate(top_5):
            f.write(f"{i+1}. **{c['name']}** ({c['url']}) - Threat Score: {c['score']}/10\n")
        f.write("\n---\n\n")

    # PHASE 4: Deep Dive War Plans
    print(f"Phase 4: Writing Deep-Dive War Plans for the Top 5...")
    
    for idx, comp in enumerate(top_5):
        print(f"Deep analyzing Threat #{idx+1}: {comp['name']}...")
        full_content = get_website_text(comp['url'], limit=8000)
        
        war_plan_prompt = f"""
        STRATEGIC WAR PLAN: OVERTAKING {comp['name']}
        
        CLIENT PROFILE: {client_profile}
        TARGET AUDIENCE: {config['target_audience']}
        COMPETITOR CONTENT: {full_content}
        
        Generate a massive, detailed strategic analysis.
        Sections:
        1. THE ENEMY'S FORTRESS: What is their 'unfair advantage' right now?
        2. THE CHINK IN THE ARMOR: Exactly where are they failing the audience?
        3. THE 'OVERTAKE' MANEUVER: Give my client 5 specific steps to steal their customers in the next 30 days.
        4. LONG-TERM VICTORY: How to prevent them from winning back the market share.
        
        Style: Aggressive, executive, and highly actionable.
        """
        
        try:
            comp_resp = client.chat.completions.create(
                model=config['model'],
                messages=[{"role": "user", "content": war_plan_prompt}]
            )
            
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write(f"## STRATEGIC DEEP DIVE: {comp['name']}\n")
                f.write(f"**URL:** {comp['url']}\n\n")
                f.write(f"{comp_resp.choices[0].message.content}\n\n")
                f.write("---\n\n")
        except Exception as e:
            print(f"Error on {comp['name']}: {e}")

    print(f"🏁 --- GAPLOGIC ANALYSIS COMPLETE ---")
    os.startfile(os.path.abspath(report_path))

if __name__ == "__main__":
    run_market_conqueror()
