import streamlit as st
import requests

import re 
from bs4 import BeautifulSoup
import pandas as pd
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
# --- 1. CONFIGURATION ---
tech_signatures = {
    # Ad Platforms (High Value)
    "TikTok Ads":      {"pattern": r"analytics\.tiktok\.com|tiktok-pixel", "points": 15},
    "Meta Ads":        {"pattern": r"connect\.facebook\.net|fbevents\.js|fbq\(", "points": 10},
    "Google Ads":      {"pattern": r"googletagmanager\.com|gtag\(|googleadservices", "points": 5},
    "Snapchat Ads":    {"pattern": r"sc-static\.net|snaptr\(", "points": 10},
    "LinkedIn Insights": {"pattern": r"snap\.licdn\.com|linkedin_data_partner_id", "points": 10},

    # Email & Marketing (Mid Value)
    "Klaviyo":         {"pattern": r"klaviyo\.com|company_id", "points": 10},
    "Mailchimp":       {"pattern": r"chimpstatic\.com|mailchimp", "points": 5},
    "HubSpot":         {"pattern": r"js\.hs-scripts\.com|hs-analytics", "points": 10},
    "Hotjar":          {"pattern": r"static\.hotjar\.com|hjid", "points": 5},

    # E-commerce & CMS (Context)
    "Shopify":         {"pattern": r"myshopify\.com|shopify\.cdn", "points": 20},
    "WordPress":       {"pattern": r"wp-content|wp-includes", "points": 5},
    "WooCommerce":     {"pattern": r"woocommerce", "points": 10},
    "Stripe":          {"pattern": r"js\.stripe\.com", "points": 15},
    "PayPal":          {"pattern": r"paypal\.com\/sdk", "points": 10}
}
# --- 2. FUNCTIONS ---
@st.cache_data
def analyze_url(url):
    # Ensure URL has http://
    if not url.startswith('http'):
        url = 'https://' + url
        
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Scan Script Tags
        tags = soup.find_all(['script', 'link'])
        raw_code = " ".join(map(str, tags))
        
        found_signals = []
        score = 0
        
        for tech, data in tech_signatures.items():
            if re.search(data["pattern"], raw_code, re.IGNORECASE):
                found_signals.append(tech)
                score += data["points"]
        
        # Success Return
        return {"URL": url, "Score": score, "Tech": ", ".join(found_signals), "Status": "Success"}
        
    except Exception as e:
        # Error Return (This was the broken part)
        return {"URL": url, "Score": 0, "Tech": "", "Status": f"Error: {e}"}
        
st.set_page_config(page_title="Signal IQ", page_icon="⚡")
st.title("⚡ Signal IQ:tech score analyzer")
st.markdown("Analyze websites for tech signals and get a tech score.")
url_input = st.text_area("Enter URLs (one per line):")
if st.button("🚀 Run Scan"):
    if not url_input:
        st.warning("Please enter at least one URL.")
    else:
        urls = [line.strip() for line in url_input.splitlines() if line.strip()]
        progress_bar = st.progress(0)
        results = []
        for i,url in enumerate(urls):
            data = analyze_url(url)
            results.append(data)
            progress_bar.progress((i + 1) / len(urls))
        st.success("Scan complete!")
        # --- NEW DASHBOARD METRICS ---
        df = pd.DataFrame(results) # We create the DF earlier now
        
        # Create 3 columns for metrics
        col1, col2, col3 = st.columns(3)
        
        # Calculate stats
        avg_score = round(df['Score'].mean(), 1)
        top_score = df['Score'].max()
        success_rate = len(df[df['Status'] == 'Success'])
        
        # Display stats
        col1.metric("Sites Scanned", len(urls))
        col2.metric("Average Wealth Score", avg_score)
        col3.metric("Highest Score", top_score)
        
        st.divider() # Adds a nice line separator
        # -----------------------------
        
        # (Your existing table code continues here...)
        st.dataframe(df.style.highlight_max(axis=0, subset=['Score']), use_container_width=True)
