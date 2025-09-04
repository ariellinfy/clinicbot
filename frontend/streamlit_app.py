
import os
import requests
from datetime import datetime
import markdown as md
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# --- Page config ---
st.set_page_config(page_title="TCM Clinic Chatbot", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# ---- Helpers ----
def fmt_ts(ts: str) -> str:
    try:
        # display local time (server time)
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts or ""
    
def post_json(url: str, payload: dict, timeout: int = 30):
    return requests.post(url, json=payload, timeout=timeout)

# --- Custom CSS ---
st.markdown("""
<style>
    .block-container { padding-bottom: 2rem; }

    .chat-container {
        max-height: calc(100vh - 250px); /* room for header + sticky input */
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        background-color: #f9f9f9;
    }

    .user-message, .assistant-message {
        padding: 0.5rem 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        word-wrap: break-word;
    }
    .user-message {
        background-color: #007bff;
        color: #fff;
        margin-left: 20%;
        text-align: right;
    }
    .assistant-message {
        background-color: #e9ecef;
        color: #333;
        margin-right: 20%;
    }

    .meta-row {
        display: flex;
        gap: .5rem;
        font-size: 0.75rem;
        color: #666;
        margin-top: 0.25rem;
        align-items: center;
        justify-content: flex-end; /* default; overridden for assistant */
    }
    .assistant-message .meta-row { justify-content: flex-start; }
    .user-message .meta-row { justify-content: flex-end; color: #fff; }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = "sess-" + os.urandom(4).hex()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_connected" not in st.session_state:
    st.session_state.api_connected = False
if "api_key_mask" not in st.session_state:
    st.session_state.api_key_mask = ""

# Initial assistant greeting (once)
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "👋 Hello! I'm here to help you with information about our clinic services. How can I assist you today?",
        "timestamp": datetime.now().isoformat()
    })
    
# --- Header ---
st.title("🧑‍⚕️ Clinic Chatbot (Demo)")
st.caption("Hello! I'm your medical clinic assistant. I can help answer general questions about our services, but please note that I cannot provide medical diagnoses or advice. For appointments, please use our booking system.")
st.caption("您好！我是您的醫療診所助手。我可以幫助回答有關我們服務的一般問題，但請注意我無法提供醫療診斷或建議。如需預約，請使用我們的預約系統。")

# --- Sidebar ---
with st.sidebar:
    st.subheader("API connection")

    api_key_input = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password", placeholder="sk-...")
    connect = st.button("🔌 Connect")

    if connect:
        key = (api_key_input or "").strip()
        if not key:
            st.error("Please paste a valid OpenAI API key.")
        else:
            try:
                resp = post_json(f"{API_BASE}/set-api-key", {"api_key": key}, timeout=30)
                data = resp.json() if resp is not None else {}
                if resp.status_code == 200 and data.get("ok"):
                    st.session_state.api_connected = True
                    st.session_state.api_key_mask = f"{key[:4]}...{key[-4:]}"
                    st.success(f"Connected (key: {st.session_state.api_key_mask})")
                    st.toast("OpenAI key connected ✓", icon="✅")
                else:
                    st.session_state.api_connected = False
                    msg = data.get("detail") or data.get("error") or "Invalid API key"
                    st.error(f"Could not set API key: {msg}")
            except Exception as e:
                st.session_state.api_connected = False
                st.error(f"Connection error: {e}")

    if st.session_state.api_connected:
        st.caption(f"✅ Connected • {st.session_state.api_key_mask}")
    else:
        st.warning("Enter your OpenAI API key and click **Connect** to start.")

    st.divider()
    st.subheader("Session")
    st.caption("ID: " + st.session_state.session_id[:8])
    if st.button("🗑️ Clear Chat"):
        try:
            post_json(f"{API_BASE}/reset-session", {"session_id": st.session_state.session_id}, timeout=30)
        except Exception as e:
            st.error(f"Reset error: {e}")
        st.session_state.messages = []
        st.toast("Session reset.", icon="✅")
        st.rerun()
        
    st.link_button("📅 Book on JaneApp", "https://demo.janeapp.com", help="Opens JaneApp booking page")
    
    if st.button("ℹ️ Sample Questions"):
        st.markdown("""
            **English:**
            - What services do you offer?
            - What are your hours on Monday?
            - How much does acupuncture cost?
            - Can I book an appointment?

            **中文:**
            - 你們提供哪些服務？
            - 週一的營業時間是什麼？
            - 針灸治療多少錢？
            - 我可以預約嗎？
        """)
    
    st.divider()
    st.subheader("Need Help? / 需要幫助？")
    st.markdown("""
        If the AI assistant cannot help with your specific question, please contact us directly:
        如果 AI 助手無法解答您的特定問題，請直接聯繫我們：
    """)
    st.markdown("""
        **Phone / 電話:** XXX-XXX-XXX  
        **Email / 電子郵件:** clinic@example.com
    """)
    st.divider()
    st.subheader("Important Disclaimer")
    st.markdown(
    """
        - General information only — **not** medical advice  
        - For health concerns, consult qualified professionals  
        - In emergencies, call local emergency services  
        - **No PII stored**
    """)
    
# ---- Chat thread ----
def render_message(message):
    ts = fmt_ts(message.get("timestamp", ""))
    content_html = md.markdown(
        message["content"],
        extensions=["extra", "sane_lists"]  # optional, better markdown
    )
    
    if message["role"] == "user":
        st.markdown(f"""
        <div class="user-message">
            {content_html}
            <div class="meta-row">
                <span>{ts}</span>
                <span>•</span>
                <span>You</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            {content_html}
            <div class="meta-row">
                <span>Assistant</span>
                <span>•</span>
                <span>{ts}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
            
for message in st.session_state.messages:
    render_message(message)
        
# ---- Input (gated until connected) ----
prompt = st.chat_input("Type your message here / 在此輸入您的訊息", disabled=not st.session_state.api_connected)
if not st.session_state.api_connected:
    st.info("Enter your OpenAI API key in the sidebar and click **Connect** to start.")
    
if prompt:
    user_prompt = {
        "role": "user", 
        "content": prompt.strip(),
        "timestamp": datetime.now().isoformat()
        }
    st.session_state.messages.append(user_prompt)
    render_message(user_prompt)
    
    with st.spinner("Assistant is typing..."):
        try:
            r = post_json(
                f"{API_BASE}/chat",
                {"message": prompt, "session_id": st.session_state.session_id},
                timeout=120,
            )
            if r.status_code == 401:
                st.session_state.api_connected = False
                reply = "Your OpenAI API key is not set or invalid. Please enter it in the sidebar and click **Connect**."
            else:
                data = r.json()
                reply = data.get("reply", "").strip() or "Sorry, I couldn't generate a response."
        except Exception:
            reply = "I'm sorry, I'm having trouble responding right now. Please try again later or contact our staff directly."

    assistant_message = {"role": "assistant", "content": reply, "timestamp": datetime.now().isoformat()}
    st.session_state.messages.append(assistant_message)
    render_message(assistant_message)
        
# ---- Footer ----
st.markdown("---")
st.caption("⚠️ This AI assistant provides general information only and should not replace professional medical advice.")