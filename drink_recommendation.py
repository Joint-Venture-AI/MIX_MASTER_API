from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI
import logging
import json

# Initialize Flask app and CORS
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Verify OpenAI API key
if not openai_api_key:
    logger.error("OpenAI API key not found in .env file")
    raise ValueError("OpenAI API key not found")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Test OpenAI API connection
try:
    test_response = client.models.list()
    logger.info("OpenAI API connection successful")
except Exception as e:
    logger.error(f"OpenAI API connection failed: {str(e)}")
    raise ValueError("OpenAI API connection failed")


# Helper function to validate input
def validate_input(data):
    required_fields = ["mood", "weather", "location"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing or empty field: {field}"
    return True, ""


# Helper function to get a public image URL for a dish or drink
def get_image_url(name):
    return f"https://source.unsplash.com/featured/?{name.replace(' ', '%20')}"


# Helper function to generate recommendation using OpenAI
def generate_recommendation(mood, weather, location):
    prompt = f"""
Based on the mood '{mood}', weather '{weather}', and location '{location}', suggest a location-specific alcoholic drink and suitable food pairings.

The drink should reflect the local culture or ingredients of {location}. Return your result in this exact JSON format:

{{
  "drink": {{
    "name": str,
    "type": str,
    "alcohol_base": str,
    "description": str,
    "alcohol_content": str
  }},
  "food_pairings": [
    {{
      "name": str,
      "description": str
    }}
  ]
}}

Only return the JSON object. Do not include markdown or explanations.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary and mixology expert specializing in local food and drink recommendations.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )
        # Extract and parse the response
        result = response.choices[0].message.content
        result = result.strip().lstrip("```json").rstrip("```").strip()

        recommendation = json.loads(result)

        # Add image URLs
        recommendation["drink"]["image"] = get_image_url(
            recommendation["drink"]["name"]
        )
        for food in recommendation["food_pairings"]:
            food["image"] = get_image_url(food["name"])

        return recommendation
    except Exception as e:
        logger.error(f"Error generating recommendation: {str(e)}")
        return None


@app.route("/api/drink_recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        # Validate input
        is_valid, error_message = validate_input(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400

        mood = data["mood"]
        weather = data["weather"]
        location = data["location"]
        logger.info(
            f"Received request: mood={mood}, weather={weather}, location={location}"
        )

        # Generate recommendation
        recommendation = generate_recommendation(mood, weather, location)
        if not recommendation:
            return jsonify({"error": "Failed to generate recommendation"}), 500

        # Structure the response
        response = {
            "mood": mood,
            "weather": weather,
            "location": location,
            "recommendation": recommendation,
        }
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
