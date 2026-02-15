import streamlit as st
import os
import requests
import ssl
import socket
import time
from datetime import datetime
from duckduckgo_search import DDGS

# ============================================================
# NO CREWAI — everything built from scratch
# ============================================================

KEYGEN_ACCOUNT_ID = ""
try:
    KEYGEN_ACCOUNT_ID = st.secrets.get("KEYGEN_ACCOUNT_ID", "")
except:
    pass

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
# LLM — HF Inference Providers router
#
# The new router requires a WRITE token (not Read).
# Endpoint: POST https://router.huggingface.co/v1/chat/completions
# Model format: "provider/org/model"  e.g. "together/meta-llama/Llama-3.3-70B-Instruct"
# ============================================================
class LLM:
    BASE_URL = "https://router.huggingface.co/v1/chat/completions"

    # Models available on HF Inference Providers router
    # Format: just the model ID, HF router picks the provider automatically
    MODELS = {
        "Llama 3.3 70B (Best)":   "meta-llama/Llama-3.3-70B-Instruct",
        "Qwen 2.5 72B (Smart)":   "Qwen/Qwen2.5-72B-Instruct",
        "Mistral Small (Fast)":   "mistralai/Mistral-Small-24B-Instruct-2501",
    }

    def __init__(self, api_key, model_id="meta-llama/Llama-3.3-70B-Instruct"):
        self.api_key = api_key
        self.model = model_id

    def call(self, prompt: str, max_new_tokens: int = 1500) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_new_tokens,
            "temperature": 0.7,
        }

        for attempt in range(2):
            try:
                resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=120)

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()

                if resp.status_code == 503 and attempt == 0:
                    time.sleep(20)
                    continue

                # Friendly error messages
                if resp.status_code == 401:
                    return "❌ Invalid API key. Check your HUGGINGFACE_API_KEY."
                if resp.status_code == 402:
                    return "❌ Payment required. Enable billing at https://huggingface.co/settings"
                if resp.status_code == 403:
                    return (
                        "❌ Permission denied.\n\n"
                        "Your token needs WRITE access.\n"
                        "Go to https://huggingface.co/settings/tokens\n"
                        "→ Delete your old token\n"
                        "→ Create a new one with the 'Write' tab selected\n"
                        "→ Paste the new token into secrets.toml"
                    )
                if resp.status_code == 429:
                    return "⏳ Rate-limit hit. Wait 60 s and try again."
                if resp.status_code == 404:
                    return f"❌ Model '{self.model}' not found on this provider."

                return f"❌ HTTP {resp.status_code}: {resp.text[:300]}"

            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue
                return "❌ Request timed out."
            except Exception as e:
                return f"❌ Error: {e}"

        return "⏳ Model still loading — try again in 30 s."


# ============================================================
# TOOLS
# ============================================================
class SSLTool:
    name = "SSL Inspector"

    def run(self, target: str) -> str:
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


class SearchTool:
    name = "Web Search"

    def run(self, target: str) -> str:
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


class ScraperTool:
    name = "Web Scraper"

    def run(self, target: str) -> str:
        try:
            resp = requests.get(target, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            low = resp.text.lower()
            checks = {
                "React": ["react", "reactdom"],
                "Vue.js": ["vue.js", "vue.min"],
                "Angular": ["angular", "ng-app"],
                "Next.js": ["__next", "next.js"],
                "WordPress": ["wp-content", "wordpress"],
                "Shopify": ["shopify", "cdn.shopify"],
                "Bootstrap": ["bootstrap"],
                "Tailwind CSS": ["tailwind"],
                "jQuery": ["jquery"],
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
# AGENT  — same constructor as CrewAI's Agent()
# ============================================================
class Agent:
    def __init__(self, role, goal, backstory, llm,
                 tools=None, verbose=True, allow_delegation=False):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm
        self.tools = tools or []
        self.verbose = verbose
        self.allow_delegation = allow_delegation

    def execute(self, task_description: str, context: str = "") -> str:
        # 1. run every tool
        tool_output = ""
        for tool in self.tools:
            tool_output += f"\n[{tool.name} output]\n{tool.run(task_description)}\n"

        # 2. build prompt
        prompt = (
            f"You are the {self.role}.\n"
            f"Background: {self.backstory}\n"
            f"Goal: {self.goal}\n\n"
        )
        if context:
            prompt += f"Context from previous agents:\n{context}\n\n"
        if tool_output:
            prompt += f"Tool results:\n{tool_output}\n\n"
        prompt += (
            f"Task: {task_description}\n\n"
            f"Provide a detailed, professional response."
        )

        return self.llm.call(prompt)


# ============================================================
# TASK  — same constructor as CrewAI's Task()
# ============================================================
class Task:
    def __init__(self, description, agent, expected_output=""):
        self.description = description
        self.agent = agent
        self.expected_output = expected_output


# ============================================================
# CREW  — same constructor as CrewAI's Crew()
# ============================================================
class Crew:
    def __init__(self, agents, tasks, verbose=True, process=None):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose

    def kickoff(self) -> str:
        context = ""
        last_result = ""
        for task in self.tasks:
            agent = task.agent
            if self.verbose:
                st.write(f"  👤 **{agent.role}** is working…")
            result = agent.execute(task.description, context=context)
            context += f"\n--- {agent.role} output ---\n{result}\n"
            last_result = result
            if self.verbose:
                st.write(f"  ✅ **{agent.role}** finished.")
        return last_result


# ============================================================
# SWARM ORCHESTRATOR
# ============================================================
def run_swarm(mode, target, llm):
    ssl_tool    = SSLTool()
    search_tool = SearchTool()
    scrape_tool = ScraperTool()

    # ---- AGENTS ----
    ceo = Agent(
        role='CEO',
        goal='Oversee operations and ensure quality results',
        backstory='You are the strategic leader.',
        verbose=True,
        llm=llm,
        allow_delegation=True
    )

    lead_scout = Agent(
        role='Lead Scout',
        goal='Find high-quality business leads',
        backstory='You find relevant businesses online.',
        tools=[search_tool],
        verbose=True,
        llm=llm
    )

    manager_tech = Agent(
        role='CTO',
        goal='Audit technical infrastructure',
        backstory='You analyze websites and technology.',
        tools=[scrape_tool, ssl_tool],
        verbose=True,
        llm=llm
    )

    # ---- TASKS + CREW ----
    if mode == "lead_gen":
        task1 = Task(
            description=f"Search the web and find 5 businesses in this niche: '{target}'. "
                        f"For each business list the name, URL, and a short description.",
            agent=lead_scout,
            expected_output="A list of 5 businesses with name, URL, and description."
        )
        task2 = Task(
            description="Review the leads found by the Lead Scout. "
                        "Rank them by potential and explain why each is a good lead.",
            agent=ceo,
            expected_output="A ranked list of leads with strategic reasoning."
        )
        crew = Crew(agents=[ceo, lead_scout], tasks=[task1, task2], verbose=True)

    else:
        task1 = Task(
            description=f"Audit this website: {target}. "
                        f"Use the Web Scraper to analyze its code and the SSL Inspector to check its certificate. "
                        f"Report your findings in detail.",
            agent=manager_tech,
            expected_output="A technical audit report covering tech stack and SSL status."
        )
        task2 = Task(
            description="Review the CTO's audit findings. "
                        "Write an executive summary with actionable recommendations.",
            agent=ceo,
            expected_output="An executive summary with actionable recommendations."
        )
        crew = Crew(agents=[ceo, manager_tech], tasks=[task1, task2], verbose=True)

    return crew.kickoff()


# ============================================================
# KEYGEN AUTH
# ============================================================
def validate_license(key):
    if not KEYGEN_ACCOUNT_ID:
        st.error("❌ Keygen Account ID missing in secrets!")
        return False
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

    # --- sidebar key status ---
    with st.sidebar.expander("🤖 AI Status", expanded=True):
        if HF_KEY:
            st.success("✅ Hugging Face Connected")
            st.caption(f"Key: hf_…{HF_KEY[-6:]}")
        else:
            st.error("❌ HUGGINGFACE_API_KEY not found")
            st.code('HUGGINGFACE_API_KEY = "hf_your_token"\nKEYGEN_ACCOUNT_ID = "your_id"', language="toml")

    # --- auth ---
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

    # --- no key ---
    if not HF_KEY:
        st.error("🚫 HUGGINGFACE_API_KEY is missing!")
        st.markdown("### Setup (token MUST be Write type):")
        st.markdown("1. Go to **https://huggingface.co/settings/tokens**")
        st.markdown("2. Click **New Token**")
        st.markdown("3. Select the **Write** tab (NOT Read)")
        st.markdown("4. Name it anything → **Generate**")
        st.markdown("5. **Copy** the token")
        st.markdown("6. Add to `.streamlit/secrets.toml`:")
        st.code('HUGGINGFACE_API_KEY = "hf_paste_here"\nKEYGEN_ACCOUNT_ID = "your_id"', language="toml")
        st.stop()

    # --- controls ---
    st.sidebar.title("⚙️ Swarm Controls")

    model_choice = st.sidebar.selectbox("AI Model:", LLM.MODELS.keys())
    llm = LLM(api_key=HF_KEY, model_id=LLM.MODELS[model_choice])

    mode = st.sidebar.radio("Swarm Mode:", ["Deep Audit", "Lead Hunter"])
    with st.sidebar.expander("👥 Active Agents"):
        st.write("👔 **CEO** — Strategic oversight")
        if mode == "Lead Hunter":
            st.write("🔍 **Lead Scout** — Web Search")
        else:
            st.write("💻 **CTO** — Web Scraper + SSL Inspector")

    # --- main ---
    st.title(f"⚡ Signal IQ AI Swarm: {mode}")
    if mode == "Deep Audit":
        st.info("Agents: **CEO + CTO** will audit security and tech stack.")
        target = st.text_input("Target URL:", placeholder="https://example.com")
    else:
        st.info("Agents: **CEO + Lead Scout** will find and rank businesses.")
        target = st.text_input("Target Niche:", placeholder="Gyms in London")

    if st.button("🚀 Deploy AI Swarm", type="primary", disabled=not target):
        st.markdown("---")
        st.subheader("🤖 Swarm Executing…")
        with st.status("Agents working…", expanded=True) as status:
            st.write(f"🎯 Target: {target}")
            st.write(f"🤖 Model: {model_choice}")
            st.write(f"👥 Agents: CEO + {'Lead Scout' if 'Hunter' in mode else 'CTO'}")
            try:
                result = run_swarm(
                    "lead_gen" if "Hunter" in mode else "audit",
                    target, llm
                )
                status.update(label="✅ Swarm Complete!", state="complete", expanded=False)
            except Exception as e:
                import traceback
                status.update(label="❌ Error", state="error")
                st.error(str(e))
                st.code(traceback.format_exc())
                result = None

        if result:
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