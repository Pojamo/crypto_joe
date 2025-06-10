import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import openai
import random

# --- CONFIG ---
st.set_page_config(page_title="Crypto Joe Dashboard", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- CAPTCHA ---
if "captcha_passed" not in st.session_state:
    st.session_state.captcha_passed = False
if "captcha_a" not in st.session_state or "captcha_b" not in st.session_state:
    st.session_state.captcha_a = random.randint(1, 9)
    st.session_state.captcha_b = random.randint(1, 9)

if not st.session_state.captcha_passed:
    st.header("🔒 Simple Captcha Verification")
    a = st.session_state.captcha_a
    b = st.session_state.captcha_b
    captcha_input = st.text_input(f"What is {a} + {b}? (anti-bot)")
    if st.button("Verify"):
        if captcha_input.strip() == str(a + b):
            st.session_state.captcha_passed = True
            st.success("Captcha passed! Welcome.")
        else:
            st.error("Incorrect. Please try again.")
            st.session_state.captcha_a = random.randint(1, 9)
            st.session_state.captcha_b = random.randint(1, 9)
    st.stop()

# --- DATA FETCH BTC & ADA (CoinGecko) ---
def fetch_data(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": "90", "interval": "daily"}
    r = requests.get(url, params=params)
    data = r.json()
    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    volumes = pd.DataFrame(data["total_volumes"], columns=["timestamp", "volume"])
    df = pd.merge(df, volumes, on="timestamp")
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("date", inplace=True)
    df = df[["price", "volume"]]
    # RSI
    delta = df["price"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

btc_df = fetch_data("bitcoin")
ada_df = fetch_data("cardano")

# --- CORE VALUES ---
btc_now = btc_df["price"].iloc[-1]
btc_change = btc_df["price"].pct_change().iloc[-1] * 100
btc_rsi = btc_df["RSI"].iloc[-1]

ada_now = ada_df["price"].iloc[-1]
ada_change = ada_df["price"].pct_change().iloc[-1] * 100
ada_rsi = ada_df["RSI"].iloc[-1]

# --- PROMPT (Crypto Joe persona) ---
prompt = f"""
Act as Crypto Joe: a no-nonsense macro & crypto market analyst — a fusion of Mark Moss’s historical insight, George Gammon’s macro focus, Benjamin Cowen’s data-driven cycle analysis, and Wolves of Crypto’s pragmatic style.
Be sharp, concise, realistic, and slightly witty. Avoid hype. Focus on connections between macro, on-chain, and price action.
Give a short English market update with:
- Current Bitcoin price (~${btc_now:,.0f})
- Today’s % change for Bitcoin ({btc_change:+.2f}%)
- RSI for Bitcoin ({btc_rsi:.0f})
- Cardano price (~${ada_now:,.3f})
- Today’s % change for Cardano ({ada_change:+.2f}%)
- RSI for Cardano ({ada_rsi:.0f})
- Macro context (Fed, CPI, ETF flows, etc)
- Technical trend and what to watch next for both coins
End with a signature Crypto Joe one-liner.
"""

# --- GPT (new OpenAI 1.x syntax) ---
if "joe_update" not in st.session_state:
    with st.spinner("Generating Joe's update..."):
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.9
        )
        st.session_state.joe_update = response.choices[0].message.content

joe_text = st.text_area("Generated Crypto Joe Update:", st.session_state.joe_update, height=200)

# --- DISCORD WEBHOOK ---
st.markdown("### 🔗 Send to Discord")
webhook_url = st.text_input("Paste your Discord webhook URL")
if st.button("Post to Discord"):
    if webhook_url:
        response = requests.post(webhook_url, json={"content": joe_text})
        if response.status_code == 204:
            st.success("✅ Successfully posted to Discord!")
        else:
            st.error(f"❌ Failed to send. Status code: {response.status_code}")
    else:
        st.warning("Please enter a webhook URL first.")

# --- CHART BTC & ADA ---
st.markdown("### 📈 BTC & ADA Chart")
fig, axs = plt.subplots(4, 1, figsize=(12, 12), sharex=True, gridspec_kw={'height_ratios': [3, 1, 3, 1]})
fig.suptitle('Bitcoin & Cardano – Price, RSI, Volume (90 days)', fontsize=16)

# BTC Price & Volume
axs[0].plot(btc_df.index, btc_df["price"], label="BTC Price", color="black")
axs[0].set_ylabel("BTC Price (USD)")
axs[0].legend()
axs[0].grid(True)
axs[1].plot(btc_df.index, btc_df["RSI"], label="BTC RSI", color="purple")
axs[1].axhline(70, color="red", linestyle="--")
axs[1].axhline(30, color="green", linestyle="--")
axs[1].set_ylabel("BTC RSI")
axs[1].legend()
axs[1].grid(True)

# ADA Price & Volume
axs[2].plot(ada_df.index, ada_df["price"], label="ADA Price", color="blue")
axs[2].set_ylabel("ADA Price (USD)")
axs[2].legend()
axs[2].grid(True)
axs[3].plot(ada_df.index, ada_df["RSI"], label="ADA RSI", color="orange")
axs[3].axhline(70, color="red", linestyle="--")
axs[3].axhline(30, color="green", linestyle="--")
axs[3].set_ylabel("ADA RSI")
axs[3].legend()
axs[3].grid(True)

plt.tight_layout()
plt.subplots_adjust(top=0.92)
st.pyplot(fig)

st.caption("Powered by CoinGecko API + OpenAI + Streamlit | Crypto Joe 🔥")
