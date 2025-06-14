import base64
import json
import os
import re
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from openai import OpenAI

# Load API key from .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise EnvironmentError("❌ OPENAI_API_KEY not found in .env file")

# Configure OpenAI client
client = OpenAI(api_key=openai_api_key)

app = Flask(__name__)

# Folder to save uploaded images
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_json(text: str):
    """Try to extract JSON object from text using regex."""
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not json_match:
        return None
    try:
        return json.loads(json_match.group(1))
    except json.JSONDecodeError:
        return None


def generate_recipe(image_path: str, description: str) -> dict | None:
    """Generate cocktail recipe JSON by sending image and description to OpenAI."""
    try:
        # Read the image file and convert to base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        # Format as a data URL with MIME type
        base64_image = f"data:image/jpeg;base64,{image_data}"

        prompt = f"""
You are a professional mixologist and beverage expert.

Analyze the alcohol bottle shown in this image.

Use the following user description for extra context: "{description}".

Based on this, generate a complete structured JSON object that includes accurate cocktail metadata, flavor insights, mixology steps, and pairing suggestions.

⚠️ Output ONLY valid JSON. Do NOT include explanations, markdown, or any extra text.

The JSON schema must exactly match this structure:
{{
  "name": "name of the alochol",
  "alcohol_content": "String",
  "type": "String",
  "description": "String",
  "image": "String",
  "flavor_profile": "String",
  "strength": "String",
  "difficulty": "String",
  "glass": "String",
  "rating": {{
    "score": Float,
    "total_ratings": Integer
  }},
  "tags": ["String"],
  "ingredients": [
    {{
      "name": "String",
      "amount": "String",
      "category": "String"
    }}
  ],
  "garnish": ["String"],
  "instructions": {{
    "how_to_make": "String",
    "steps": [
      {{
        "step": Integer,
        "title": "String",
        "instruction": "String",
        "tip": "String"
      }}
    ]
  }},
  "variations": [
    {{
      "name": "String",
      "description": "String",
      "key_ingredient": "String"
    }}
  ],
  "serving_info": {{
    "best_time": "String",
    "occasion": "String",
    "temperature": "String",
    "garnish_placement": "String"
  }},
  "nutritional_info": {{
    "calories": Integer,
    "alcohol_content": "String",
    "sugar_content": "String"
  }},
  "pairing_recommendations": [
    {{
      "category": "String",
      "items": ["String"],
      "emoji": "String"
    }}
  ],
  "professional_tips": ["String"],
  "history": {{
    "origin": "String",
    "creator": "String",
    "year_created": "String",
    "story": "String"
  }}
}}
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": base64_image}},
                    ],
                }
            ],
            max_tokens=4000,
        )

        raw_text = response.choices[0].message.content.strip()
        data = extract_json(raw_text)
        if not data:
            print("❌ Failed to parse JSON from OpenAI response.")
            print(f"Raw response:\n{raw_text}")
        return data

    except Exception as e:
        print(f"❌ Exception in generate_recipe(): {e}")
        return None


@app.route("/generate-cocktail", methods=["POST"])
def cocktail_api():
    if "image" not in request.files or "description" not in request.form:
        return jsonify({"error": "Missing image or description"}), 400

    image_file = request.files["image"]
    description = request.form["description"]

    try:
        # Save uploaded image with unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(save_path)

        # Generate cocktail data from the saved image file and description
        data = generate_recipe(save_path, description)
        if not data:
            return jsonify({"error": "Failed to generate cocktail data"}), 500

        # Add the image URL to the response for frontend display
        if data and "image" in data:
            data["image"] = request.host_url + f"uploads/{filename}"

        return jsonify(data), 200

    except Exception as e:
        print(f"❌ Error in /generate-cocktail route: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🍸 Welcome to the Cocktail Recipe Generator API"})


if __name__ == "__main__":
    app.run(debug=True)
