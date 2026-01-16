import re
import requests
import json
from bs4 import BeautifulSoup
import csv


# --- 1. CONFIGURATION ---

# We define HEADERS here so the script looks like a real browser (Chrome)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

tech_signatures = {
    "TikTok Ads":      {"pattern": r"analytics\.tiktok\.com|tiktok-pixel", "points": 15},
    "Meta Ads":        {"pattern": r"connect\.facebook\.net|fbevents\.js|fbq\(", "points": 10},
    "Google Analytics":{"pattern": r"googletagmanager\.com|ua-\d+|gtag\(", "points": 5},
    "Shopify":         {"pattern": r"myshopify\.com|shopify\.cdn", "points": 20}
}
def get_website_content(url):
    # Auto-add https:// if the user forgot it
    if not url.startswith('http'):
        url = 'https://' + url
        
    print(f"Scanning {url}...")
    
    try:
        # We pass the HEADERS dictionary here
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.text
    except Exception as e:
        return f"Error: {e}"

def analyze_target(url):
    # 1. Clean the URL
    if not url.startswith('http'):
        url = 'https://' + url

    try:
        # 2. Visit the website
        response = requests.get(url, headers=HEADERS, timeout=5)
        page_content = response.text.lower()

        # 3. Scan for "Rich Signals"
        signals_found = []
        score = 10 # Base score

        # SIGNAL 1: Facebook Pixel (Ads)
        if 'fbevents.js' in page_content or 'facebook.com/tr' in page_content:
            signals_found.append("Facebook Pixel")
            score += 25

        # SIGNAL 2: Google Tag Manager (Data)
        if 'gtm.js' in page_content or 'googletagmanager' in page_content:
            signals_found.append("GTM")
            score += 10

        # SIGNAL 3: HubSpot (Premium CRM)
        if 'hubspot.js' in page_content or 'hs-scripts.com' in page_content:
            signals_found.append("HubSpot")
            score += 30

        # SIGNAL 4: Shopify (E-commerce)
        if 'shopify' in page_content:
            signals_found.append("Shopify Store")
            score += 20

        # SIGNAL 5: Security
        if 'recaptcha' in page_content:
            signals_found.append("Google Security")
            score += 5
        keywords = ['tiktok.com', 'tiktok-pixel']

        if any(keyword in page_content for keyword in keywords):
            signals_found.append("TikTok Ads")
            score += 15
        # Check for Meta (Facebook) Pixel
        if any(x in page_content for x in ['fbevents.js', 'fbq(', 'facebook.net']):
            signals_found.append("Meta Ads")
            score += 10

        # Check for Google Analytics/Ads (GTM or gtag)
        if any(x in page_content for x in ['googletagmanager.com', 'gtag(', 'ua-']):
            signals_found.append("Google Ads/Analytics")
            score += 5
        # Configuration: Define the tech, keywords to look for, and the score value
        tech_signatures = {
            "TikTok Ads": {"keywords": ['tiktok.com', 'tiktok-pixel'], "points": 15},
            "Meta Ads":   {"keywords": ['fbevents.js', 'fbq('],        "points": 10},
            "Google Ads": {"keywords": ['googletagmanager', 'gtag('],   "points": 5},
            "Shopify":    {"keywords": ['myshopify.com', 'shopify.CHECKOUT'], "points": 20}
        }

        # The Logic Loop
        for tech, data in tech_signatures.items():
            # Check if ANY of the keywords exist in the page content
            if any(k in page_content for k in data["keywords"]):
                signals_found.append(tech)
                score += data["points"]

        print(f"Found: {signals_found}")
        print(f"Total Score: {score}")
        # Cap score at 100
        if score > 100: score = 100

        return {
            "status": "success",
            "url": url,
            "wealth_score": score,
            "tech_stack": signals_found
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
def analyze_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Get the raw code from script and link tags
    tags_to_scan = soup.find_all(['script', 'link'])
    raw_code = " ".join(map(str, tags_to_scan))
    
    found_signals = []
    total_score = 0
    
    # 2. Run ONE loop to do both jobs (Populate List + Add Score)
    for tech, data in tech_signatures.items():
        if re.search(data["pattern"], raw_code, re.IGNORECASE):
            found_signals.append(tech)        # Save the NAME
            total_score += data["points"]     # Add the SCORE
            
    return found_signals, total_score

# --- THE GATEWAY: Zoho Catalyst Handler ---
def handler(context, basicio):
    try:
        target_url = basicio.get_argument("url") 
    except:
        basicio.write(json.dumps({"error": "No URL provided"}))
        context.close()
        return

    result_data = analyze_target(target_url)
    basicio.write(json.dumps(result_data))
    context.close()
# This simulates a website that uses Shopify and Facebook, 
# but simply writes about TikTok (False positive test)
mock_website_html = """
<html>
<head>
    <script src="https://cdn.myshopify.com/s/files/1/test.js"></script>
    <script>
        !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
        n.callMethod.apply(n,arguments):n.queue.push(arguments)};
        if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
        n.queue=[];t=b.createElement(e);t.async=!0;
        t.src=v;s=b.getElementsByTagName(e)[0];
        s.parentNode.insertBefore(t,s)}(window, document,'script',
        'https://connect.facebook.net/en_US/fbevents.js');
    </script>
</head>
<body>
    <h1>How to run TikTok Ads</h1>
    <p>We are experts at setting up the tiktok-pixel for you.</p>
</body>
</html>
"""

# Run the analyzer
signals, score = analyze_html(mock_website_html)

# --- 4. OUTPUT ---
print("-" * 30)
print(f"Signals Detected: {signals}")
print(f"Lead Score:       {score}")
print("-" * 30)

# ... (Your imports and functions are above this) ...

# --- 3. MAIN EXECUTION BLOCK ---
if __name__ == "__main__":

    # The list of websites to scan (You can eventually load this from a file)
    target_websites = [
        "allbirds.com",
        "gymshark.com", 
        "colourpop.com",
        "zoho.com",      # Will likely score 0 (Protected/Dynamic)
        "tesla.com"
    ]

    print(f"\n--- STARTING BULK SCAN ({len(target_websites)} sites) ---\n")
    
    # We will store all results here
    results_database = []

    for url in target_websites:
        # Clean the URL
        if not url.startswith('http'):
            clean_url = 'https://' + url
        else:
            clean_url = url

        print(f"Scanning {clean_url}...")
        
        # 1. Fetch & Analyze
        html = get_website_content(clean_url)
        signals, score = analyze_html(html)
        
        # 2. Add to our database list
        results_database.append({
            "URL": clean_url,
            "Score": score,
            "Tech Stack": ", ".join(signals) # Converts list to string "Meta, Shopify"
        })

    # --- 4. SAVE TO CSV ---
    csv_filename = "scan_results.csv"
    
    # Writing the file
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["URL", "Score", "Tech Stack"])
        writer.writeheader()
        writer.writerows(results_database)

    print(f"\n[SUCCESS] Scanned {len(target_websites)} sites.")
    print(f"Results saved to: {csv_filename}")
