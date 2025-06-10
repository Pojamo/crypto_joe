import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import datetime
import openai
import random

# --- CONFIG ---
st.set_page_config(page_title="Crypto Joe BTC Dashboard", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- CAPTCHA SETUP ---
st.session_state.setdefault("captcha_passed", False)
if not st.session_state.captcha_passed:
    st.header("🔒 Simple Captcha Verification")
    a, b = random.randint(1, 9), random.randint(1, 9)
    captcha_input = st.text_input(f"What is {a} + {b}? (anti-bot)")
    if st.button("Verify"):
        if captcha_input.strip() == str(a + b):
            st.session_state.captcha_passed = True
            st.success("Captcha passed! Welcome.")
        else:
            st.error("Incorrect. Please try again.")
    st.stop()

# --- TITLE ---
st.title("🧠 Crypto Joe – Daily Bitcoin Update")
st.caption("Auto-generated market insight + live BTC chart")

# --- COINGECKO DATA FETCH ---
st.subheader("📊 Live BTC Data (last 90 days)")
url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
params = {"vs_currency": "usd", "days": "90", "interval": "daily"}
resp = requests.get(url, params=params)
data = resp.json()

# --- FORMAT DATA ---
prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
volumes = pd.DataFrame(data["total_volumes"], columns=["timestamp", "volume"])
df = pd.merge(prices, volumes, on="timestamp")
df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
df.set_index("date", inplace=True)
df = df[["price", "volume"]]

# --- INDICATORS ---
df["MA50"] = df["price"].rolling(50).mean()
df["MA200"] = df["price"].rolling(200).mean()
delta = df["price"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# --- GPT PROMPT GENERATION ---
st.subheader("🧠 Crypto Joe’s Take")
btc_now = df["price"].iloc[-1]
btc_change = df["price"].pct_change().iloc[-1] * 100
rsi_now = df["RSI"].iloc[-1]

prompt = f"""
Give a short, sharp English crypto market update in the style of Crypto Joe.
Include:
- Current Bitcoin price (~${btc_now:,.0f})
- Today’s change ({btc_change:+.2f}%)
- RSI level ({rsi_now:.0f})
- Brief take on current trend and what to watch next
End with a signature Crypto Joe line.
"""

if "joe_update" not in st.session_state:
    with st.spinner("Generating Joe's update..."):
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        st.session_state.joe_update = completion.choices[0].message.content

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

# --- CHART ---
st.markdown("### 📈 BTC Chart")
fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})
fig.suptitle('Bitcoin – Price, MA50/MA200, RSI, Volume', fontsize=16)
axs[0].plot(df.index, df["price"], label="BTC Price", color="black")
axs[0].plot(df.index, df["MA50"], label="MA50", linestyle="--", color="blue")
axs[0].plot(df.index, df["MA200"], label="MA200", linestyle="--", color="orange")
axs[0].legend()
axs[0].grid(True)
axs[1].plot(df.index, df["RSI"], label="RSI", color="purple")
axs[1].axhline(70, color="red", linestyle="--")
axs[1].axhline(30, color="green", linestyle="--")
axs[1].legend()
axs[1].grid(True)
axs[2].bar(df.index, df["volume"], label="Volume", color="gray")
axs[2].legend()
axs[2].grid(True)
st.pyplot(fig)

st.caption("Powered by CoinGecko API + OpenAI + Streamlit | Crypto Joe 🔥")
