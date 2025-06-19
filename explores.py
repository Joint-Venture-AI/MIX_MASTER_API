import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# --- Setup ---
app = Flask(__name__)
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


# --- Serper Image Fetcher ---
def fetch_image_url(query):
    try:
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "q": f"{query} alcohol bottle site:drizly.com OR site:totalwine.com",
            "type": "images",
        }

        response = requests.post(
            "https://google.serper.dev/images", headers=headers, json=payload
        )
        results = response.json()
        return results.get("images", [{}])[0].get("imageUrl", "")
    except Exception as e:
        print(f"[ERROR] Serper image fetch failed: {e}")
        return ""


# --- Brand Generator ---
def get_brands_from_openai(location: str) -> list:
    prompt = f"""
Based on the location "{location}", list 5-6 well-known alcohol brands that are popular and commonly available there.

Prioritize local or nationally produced brands over international ones.
Only include internationally known brands if they are very commonly consumed in that region.

For each, include:
- brand_name
- description (1 sentence about the brand, mentioning if it's local or global)
- category (like whiskey, vodka, wine, beer, champagne, rum, etc.)

Return strictly in this JSON format:
[
  {{
    "brand_name": "Brand",
    "description": "Short description.",
    "category": "Category"
  }},
  {{
    "brand_name": "Brand",
    "description": "Short description.",
    "category": "Category"
  }},
  ...
]
"""

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that replies with JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        raw = chat_response.choices[0].message.content.strip()
        json_data = raw.replace("```json", "").replace("```", "").strip()
        brand_list = json.loads(json_data)

        # Add image URLs using Serper
        for brand in brand_list:
            brand_name = brand.get("brand_name", "")
            brand["image_url"] = fetch_image_url(brand_name)

        return brand_list

    except Exception as e:
        print(f"[ERROR] OpenAI/JSON error: {e}")
        return []


# --- API Endpoint ---
@app.route("/api/get-brands", methods=["GET"])
def get_brands_api():
    location = request.args.get("location")
    if not location:
        return jsonify({"error": "Missing 'location' parameter"}), 400

    print(f"🔍 Requesting brands for location: {location}")
    brands = get_brands_from_openai(location)

    if not brands:
        return jsonify({"error": "Failed to fetch brand data"}), 500

    return jsonify(brands)


# --- Run App ---
if __name__ == "__main__":
    app.run(debug=True, port=5001)
