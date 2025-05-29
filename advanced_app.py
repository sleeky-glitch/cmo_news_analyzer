import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from io import BytesIO
import openai
import base64

# --- CONFIGURATION ---
GITHUB_USERNAME = "sleeky-glitch"
GITHUB_REPO_NAME = "cmo_news_analyzer"
EXCEL_FILE_PATH = "merged_output.xlsx"
IMAGES_FOLDER_PATH = "images"
RAW_GITHUB_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/"
EXCEL_URL = RAW_GITHUB_URL + EXCEL_FILE_PATH

openai.api_key = st.secrets["openai"]["api_key"]

st.set_page_config(page_title="Gujarati News Search & Fake News Analyzer", page_icon="📰")
st.title("Gujarati Headlines Image Search & Fake News Analyzer")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    df = pd.read_excel(EXCEL_URL)
    df = df.dropna(subset=['image_name'])
    def extract_date(image_name):
        m = re.search(r'(\d{2}-\d{2}-\d{4})', image_name)
        return datetime.strptime(m.group(1), '%d-%m-%Y') if m else None
    df['article_date'] = df['image_name'].apply(extract_date)
    return df.sort_values('article_date', ascending=False)

df = load_data()

# --- SEARCH UI ---
tag = st.text_input("ગુજરાતી ટેગ દાખલ કરો (Enter Gujarati tag):")
if not tag:
    st.info("કૃપા કરીને ટેગ દાખલ કરો.")
    st.stop()

headline_results = df[df['headline'].str.contains(tag, case=False, na=False)]
fulltext_results = df[df['full_text'].str.contains(tag, case=False, na=False)]
results = pd.concat([headline_results, fulltext_results]).drop_duplicates().sort_values('article_date', ascending=False)

if results.empty:
    st.info("કોઈ પરિણામ મળ્યું નથી.")
    st.stop()

# --- DATE FILTER ---
dates = results['article_date'].dropna()
if not dates.empty:
    min_date, max_date = dates.min().date(), dates.max().date()
    date_range = st.date_input(
        "તારીખની રેન્જ પસંદ કરો (Select date range):",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        results = results[
            (results['article_date'].dt.date >= start_date) &
            (results['article_date'].dt.date <= end_date)
        ]

st.write(f"મળેલા પરિણામો: {len(results)}")

# --- DISPLAY RESULTS WITH ANALYZE BUTTON ---
for idx, row in results.iterrows():
    st.markdown("---")
    if pd.notnull(row['article_date']):
        st.write(f"**તારીખ:** {row['article_date'].strftime('%d-%m-%Y')}")
    image_name = row['image_name']
    image_url = f"{RAW_GITHUB_URL}{IMAGES_FOLDER_PATH}/{image_name}"
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_bytes = response.content
        st.image(BytesIO(image_bytes), caption=image_name)
        analyze_btn = st.button("Analyze", key=f"analyze_{idx}")
        if analyze_btn:
            with st.spinner("Analyzing image for fake news..."):
                mime = "image/jpeg" if image_name.lower().endswith((".jpg", ".jpeg")) else "image/png"
                b64 = base64.b64encode(image_bytes).decode()
                image_data_url = f"data:{mime};base64,{b64}"
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {"role": "system", "content": "You are a fact-checking assistant. Analyze the uploaded image for signs of fake or misleading news. If text is present, extract and analyze it. Explain your reasoning and suggest how to verify the claim, also provide a sentiment analysis and author of the claim, also try to provide original source."},
                            {"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": image_data_url}}
                            ]]
                        ],
                        max_tokens=700,
                        temperature=0.2
                    )
                    result = response.choices[0].message.content
                    st.success("Analysis complete!")
                    st.markdown("**AI Analysis:**")
                    st.write(result)
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.warning(f"Image not found or error loading image: {image_name} - {e}")

st.info("Made with <3 by BSPL")
