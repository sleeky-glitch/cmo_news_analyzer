import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from io import BytesIO

# GitHub repository details
GITHUB_USERNAME = "sleeky-glitch"
GITHUB_REPO_NAME = "cmo_news_analyzer"
EXCEL_FILE_PATH = "merged_output.xlsx"  # Path to the Excel file in the repo
IMAGES_FOLDER_PATH = "images"  # Path to the images folder in the repo

# Construct raw GitHub URLs
RAW_GITHUB_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/main/"
EXCEL_URL = RAW_GITHUB_URL + EXCEL_FILE_PATH

@st.cache_data
def load_data():
    """Loads data from the Excel file hosted on GitHub."""
    try:
        df = pd.read_excel(EXCEL_URL)
        df = df.dropna(subset=['image_name'])

        def extract_date(image_name):
            try:
                # Looking for date pattern DD-MM-YYYY
                date_match = re.search(r'(\d{2}-\d{2}-\d{4})', image_name)
                if date_match:
                    date_str = date_match.group(1)
                    return datetime.strptime(date_str, '%d-%m-%Y')
            except:
                return None

        df['article_date'] = df['image_name'].apply(extract_date)
        df = df.sort_values(by='article_date', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = load_data()

if df is None:
    st.stop()

st.title("Gujarati Headlines Image Search")

tag = st.text_input("ગુજરાતી ટેગ દાખલ કરો (Enter Gujarati tag):")

if tag:
    # Filter headlines or full_text containing the tag (case-insensitive, substring match)
    headline_results = df[df['headline'].str.contains(tag, case=False, na=False)]
    fulltext_results = df[df['full_text'].str.contains(tag, case=False, na=False)]
    results = pd.concat([headline_results, fulltext_results]).drop_duplicates()
    results = results.sort_values(by='article_date', ascending=False)

    if not results.empty:
        # Only show date filter if there are valid dates
        valid_dates = results['article_date'].dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            date_range = st.date_input(
                "તારીખની રેન્જ પસંદ કરો (Select date range):",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            # Filter results by selected date range
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                results = results[
                    (results['article_date'].dt.date >= start_date) &
                    (results['article_date'].dt.date <= end_date)
                ]

        st.write(f"મળેલા પરિણામો: {len(results)}")
        for idx, row in results.iterrows():
            if pd.notnull(row['article_date']):
                st.write(f"તારીખ: {row['article_date'].strftime('%d-%m-%Y')}")

            image_name = row['image_name']
            image_url = f"{RAW_GITHUB_URL}{IMAGES_FOLDER_PATH}/{image_name}"

            try:
                response = requests.get(image_url)
                response.raise_for_status()  # Raise an exception for bad status codes
                image = BytesIO(response.content)
                st.image(image, caption=image_name)
            except requests.exceptions.RequestException as e:
                st.warning(f"Image not found or error loading image: {image_name} - {e}")

            st.markdown("---")
    else:
        st.info("કોઈ પરિણામ મળ્યું નથી.")
else:
    st.info("કૃપા કરીને ટેગ દાખલ કરો.")
