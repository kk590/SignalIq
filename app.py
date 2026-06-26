import streamlit as st
import os
import requests
import ssl
import socket
import time
from datetime import datetime
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.prebuilt import create_react_agent

KEYGEN_ACCOUNT_ID = ""
try:
    KEYGEN_ACCOUNT_ID = st.secrets.get("KEYGEN_ACCOUNT_ID", "")
except:
    pass
if not KEYGEN_ACCOUNT_ID:
    KEYGEN_ACCOUNT_ID = os.environ.get("KEYGEN_ACCOUNT_ID", "")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# --- READ HF KEY ---
def get_hf_key():
    try:
        key = st.secrets.get("HUGGINGFACE_API_KEY", "")
        if key:
            return key
    except:
        pass
    key = os.environ.get("HUGGINGFACE_API_KEY", "")
    if key:
        return key
    try:
        for path in [".streamlit/secrets.toml", "secrets.toml"]:
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        if "HUGGINGFACE_API_KEY" in line:
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
    except:
        pass
    return ""

HF_KEY = get_hf_key()


# ============================================================
# TOOLS
# ============================================================
@tool
def ssl_inspector(target: str) -> str:
    """Inspects the SSL certificate for a given target URL."""
    hostname = target.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return f"✅ SSL VALID for {hostname}. Issuer: {cert.get('issuer','Unknown')}"
    except ssl.SSLCertVerificationError:
        return f"❌ SSL verification FAILED for {hostname}"
    except socket.timeout:
        return f"❌ Connection timed out for {hostname}"
    except Exception as e:
        return f"❌ SSL error: {e}"


@tool
def web_search(target: str) -> str:
    """Performs a web search to find businesses or general information."""
    try:
        results = DDGS().text(target, max_results=5)
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. {r.get('title','')}\n"
                f"   URL: {r.get('href','')}\n"
                f"   Info: {r.get('body','')[:150]}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ Search error: {e}"


@tool
def web_scraper(target: str) -> str:
    """Scrapes a website to determine its technology stack."""
    try:
        resp = requests.get(target, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        low = resp.text.lower()
        checks = {
            "React":      ["react", "reactdom"],
            "Vue.js":     ["vue.js", "vue.min"],
            "Angular":    ["angular", "ng-app"],
            "Next.js":    ["__next", "next.js"],
            "WordPress":  ["wp-content", "wordpress"],
            "Shopify":    ["shopify", "cdn.shopify"],
            "Bootstrap":  ["bootstrap"],
            "Tailwind CSS": ["tailwind"],
            "jQuery":     ["jquery"],
        }
        tech = [n for n, kws in checks.items() if any(k in low for k in kws)]
        tech_str = ", ".join(tech) if tech else "Standard HTML/CSS/JS"
        return (
            f"✅ Scraped {target}\n"
            f"📦 Tech Stack: {tech_str}\n\n"
            f"Source Preview:\n{resp.text[:2500]}"
        )
    except Exception as e:
        return f"❌ Scrape error: {e}"


# ============================================================
# ORCHESTRATOR
# ============================================================
def create_agent(llm, tools, system_prompt):
    return create_react_agent(llm, tools=tools, state_modifier=system_prompt)


def run_multi_agent_system(mode, target, hf_key, model_id):
    endpoint = HuggingFaceEndpoint(
        repo_id=model_id,
        huggingfacehub_api_token=hf_key,
        max_new_tokens=1500,
        temperature=0.7,
    )
    llm = ChatHuggingFace(llm=endpoint)

    ceo_prompt = "You are the CEO, the strategic leader. Oversee operations, evaluate the inputs given to you, and produce a highly detailed, professional final executive summary and recommendations."
    ceo_agent = create_agent(llm, [], ceo_prompt)

    if mode == "lead_gen":
        scout_prompt = "You are the Lead Scout. Your goal is to find high-quality business leads online. Use the web_search tool to find leads based on the target."
        scout_agent = create_agent(llm, [web_search], scout_prompt)
        
        scout_input = f"Search the web and find 5 businesses in this niche: '{target}'. For each business list the name, URL, and a short description."
        if st.session_state.get('verbose', True):
            st.write(f"  👤 **Lead Scout** is working…")
        scout_result = scout_agent.invoke({"messages": [("user", scout_input)]})
        scout_output = scout_result["messages"][-1].content
        
        ceo_input = f"Review the leads found by the Lead Scout. Rank them by potential and explain why each is a good lead.\n\nLead Scout Findings:\n{scout_output}"
        if st.session_state.get('verbose', True):
            st.write(f"  ✅ **Lead Scout** finished.")
            st.write(f"  👤 **CEO** is working…")
        ceo_result = ceo_agent.invoke({"messages": [("user", ceo_input)]})
        if st.session_state.get('verbose', True):
            st.write(f"  ✅ **CEO** finished.")
        return ceo_result["messages"][-1].content

    else:
        cto_prompt = "You are the CTO. Your goal is to audit technical infrastructure. Use the web_scraper and ssl_inspector tools to analyze the given website."
        cto_agent = create_agent(llm, [web_scraper, ssl_inspector], cto_prompt)
        
        cto_input = f"Audit this website: {target}. Use the web_scraper tool to analyze its code and the ssl_inspector tool to check its certificate. Report your findings in detail."
        if st.session_state.get('verbose', True):
            st.write(f"  👤 **CTO** is working…")
        cto_result = cto_agent.invoke({"messages": [("user", cto_input)]})
        cto_output = cto_result["messages"][-1].content
        
        ceo_input = f"Review the CTO's audit findings. Write an executive summary with actionable recommendations.\n\nCTO Findings:\n{cto_output}"
        if st.session_state.get('verbose', True):
            st.write(f"  ✅ **CTO** finished.")
            st.write(f"  👤 **CEO** is working…")
        ceo_result = ceo_agent.invoke({"messages": [("user", ceo_input)]})
        if st.session_state.get('verbose', True):
            st.write(f"  ✅ **CEO** finished.")
        return ceo_result["messages"][-1].content


# ============================================================
# KEYGEN AUTH
# ============================================================
def validate_license(key):
    if not KEYGEN_ACCOUNT_ID:
        st.warning("⚠️ KEYGEN_ACCOUNT_ID missing in secrets! Bypassing validation for local development.")
        return True
    url = f"https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}/licenses/actions/validate-key"
    hdrs = {"Content-Type": "application/vnd.api+json", "Accept": "application/vnd.api+json"}
    try:
        resp = requests.post(url, headers=hdrs, json={"meta": {"key": key}}, timeout=10)
        data = resp.json()
        if resp.status_code != 200 or data.get("errors"):
            st.error(f"❌ API Error: {data}")
            return False
        meta = data.get("meta", {})
        if not meta.get("valid"):
            st.error(f"⛔ Rejected: {meta.get('code')} - {meta.get('detail')}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False


# ============================================================
# STREAMLIT UI
# ============================================================
def main():
    st.set_page_config(page_title="Signal IQ Pro", page_icon="⚡", layout="wide")

    with st.sidebar.expander("🤖 AI Status", expanded=True):
        if HF_KEY:
            st.success("✅ Hugging Face Connected")
            st.caption(f"Key: hf_…{HF_KEY[-6:]}")
        else:
            st.error("❌ HUGGINGFACE_API_KEY not found")
            st.code('HUGGINGFACE_API_KEY = "hf_your_token"\nKEYGEN_ACCOUNT_ID = "your_id"', language="toml")

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Signal IQ Pro")
        key = st.text_input("License key:", type="password")
        if st.button("Login", type="primary"):
            with st.spinner("Validating…"):
                if validate_license(key):
                    st.session_state.authenticated = True
                    st.rerun()
        st.stop()

    if not HF_KEY:
        st.error("🚫 HUGGINGFACE_API_KEY is missing!")
        st.markdown("### Setup — token needs **Inference Providers** permission:")
        st.markdown("1. Go to **https://huggingface.co/settings/tokens**")
        st.markdown("2. Click **New token** → choose **Fine-grained**")
        st.markdown("3. Under *User permissions* → tick ✅ **Make calls to Inference Providers**")
        st.markdown("4. Click **Generate** → **Copy** the token")
        st.markdown("5. Add to `.streamlit/secrets.toml`:")
        st.code('HUGGINGFACE_API_KEY = "hf_paste_here"\nKEYGEN_ACCOUNT_ID = "your_id"', language="toml")
        st.stop()

    MODELS = {
        "Llama 3.3 70B (Best)":   "meta-llama/Llama-3.3-70B-Instruct",
        "Qwen 2.5 72B (Smart)":   "Qwen/Qwen2.5-72B-Instruct",
        "Mistral Small (Fast)":   "mistralai/Mistral-Small-24B-Instruct-2501",
    }

    st.sidebar.title("⚙️ System Controls")
    model_choice = st.sidebar.selectbox("AI Model:", MODELS.keys())
    model_id = MODELS[model_choice]

    mode = st.sidebar.radio("Operation Mode:", ["Deep Audit", "Lead Hunter"])
    with st.sidebar.expander("👥 Active Agents"):
        st.write("👔 **CEO** — Strategic oversight")
        if mode == "Lead Hunter":
            st.write("🔍 **Lead Scout** — Web Search")
        else:
            st.write("💻 **CTO** — Web Scraper + SSL Inspector")

    st.title(f"⚡ Signal IQ Multi-Agent System: {mode}")
    if mode == "Deep Audit":
        st.info("Agents: **CEO + CTO** will audit security and tech stack.")
        target = st.text_input("Target URL:", placeholder="https://example.com")
    else:
        st.info("Agents: **CEO + Lead Scout** will find and rank businesses.")
        target = st.text_input("Target Niche:", placeholder="Gyms in London")

    if st.button("🚀 Deploy Multi-Agent System", type="primary", disabled=not target):
        st.markdown("---")
        st.subheader("🤖 Multi-Agent System Executing…")
        with st.status("Agents working…", expanded=True) as status:
            st.write(f"🎯 Target: {target}")
            st.write(f"🤖 Model: {model_choice}")
            st.write(f"👥 Agents: CEO + {'Lead Scout' if 'Hunter' in mode else 'CTO'}")
            try:
                result = run_multi_agent_system(
                    "lead_gen" if "Hunter" in mode else "audit",
                    target, HF_KEY, model_id
                )
                status.update(label="✅ Multi-Agent System Complete!", state="complete", expanded=False)
            except Exception as e:
                import traceback
                status.update(label="❌ Error", state="error")
                st.error(str(e))
                st.code(traceback.format_exc())
                result = None

        if result:
            if result.startswith("❌") or result.startswith("⏳"):
                st.warning(result)
            else:
                st.success("✅ Analysis Complete!")
                st.markdown("---")
                st.markdown("## 📋 Final Report")
                st.markdown(result)
                st.download_button(
                    "📥 Download Report", result,
                    f"signaliq_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "text/plain"
                )

if __name__ == "__main__":
    main()
