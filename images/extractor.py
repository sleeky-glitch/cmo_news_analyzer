# --- IMPORTS ---

import os

os.environ["TNS_ADMIN"] = r"c:\cmobot_htmlscraper\Wallet_pocdb"

import pandas as pd
import oracledb
import re
from datetime import datetime
import boto3

# --- CONFIGURATION ---

# Oracle
oracle_user = "admin"
oracle_password = "B3y0nDAta#9999"
oracle_dsn = "pocdb_high" 

# Supabase S3
S3_ENDPOINT_URL = "https://ddtiwolodtdkiytzpaqe.supabase.co/storage/v1/s3"
S3_ACCESS_KEY_ID = "2643f38471476742492c94e2da83d737"
S3_SECRET_ACCESS_KEY = "4143e0461b81e3dba5500ad1f93be5aa03995cd7e6b6f81b31f6d97140cfd1f1"
BUCKET_NAME = "gujrati-headline-images"

# Excel and images
EXCEL_PATH = r"C:\cmobot_htmlscraper\merged_output.xlsx"
IMAGES_DIR = r"C:\cmobot_htmlscraper\images"

# --- S3 SETUP (boto3) ---
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY
)

def upload_to_s3(local_image_path, image_name):
    try:
        s3.upload_file(local_image_path, BUCKET_NAME, image_name,
                       ExtraArgs={'ContentType': 'image/jpeg'})
        public_url = f"{S3_ENDPOINT_URL}/{BUCKET_NAME}/{image_name}"
        return public_url
    except Exception as e:
        print(f"S3 upload error: {e}")
        return None

# --- ORACLE SETUP ---
try:
    connection = oracledb.connect(
        user=oracle_user,
        password=oracle_password,
        dsn=oracle_dsn,
        config_dir=r"c:\cmobot_htmlscraper\Wallet_pocdb"  # Explicitly set config directory
    )
    print("Successfully connected to Oracle Database")

    cursor = connection.cursor()

    insert_sql = """
    INSERT INTO gujarati_headlines
    (headline, full_text, image_name, image_url, article_date)
    VALUES (:1, :2, :3, :4, :5)
    """

    # --- MIGRATION ---
    df = pd.read_excel(EXCEL_PATH)
    df = df.dropna(subset=['image_name'])
    print(f"Found {len(df)} records to process")

    for index, row in df.iterrows():
        try:
            # Extract date from image name
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', row['image_name'])
            article_date = None
            if date_match:
                date_str = date_match.group(1)
                article_date = datetime.strptime(date_str, '%d-%m-%Y')

            # Upload image to S3
            local_image_path = os.path.join(IMAGES_DIR, row['image_name'])
            image_url = upload_to_s3(local_image_path, row['image_name'])

            # Insert into Oracle
            cursor.execute(insert_sql, (
                row['headline'],
                row['full_text'],
                row['image_name'],
                image_url,
                article_date
            ))
            print(f"Inserted ({index+1}/{len(df)}): {row['image_name']}")
        except Exception as e:
            print(f"Error with {row['image_name']}: {e}")

    connection.commit()
    print("All data committed to database")

except Exception as e:
    print(f"Database connection error: {e}")

finally:
    # Close resources
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'connection' in locals() and connection:
        connection.close()
        print("Database connection closed")