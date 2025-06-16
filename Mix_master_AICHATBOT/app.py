import os
import io
import uuid
import base64
from flask import Flask, request, jsonify, session
from werkzeug.utils import secure_filename
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", str(uuid.uuid4())
)  # Use env variable or random key
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Allowed alcohol-related keywords
ALCOHOL_KEYWORDS = [
    "alcohol",
    "drink",
    "wine",
    "vodka",
    "whiskey",
    "rum",
    "beer",
    "gin",
    "tequila",
    "brandy",
    "cocktail",
    "liquor",
    "spirits",
    "bottle",
    "bourbon",
]


# Helper: Check if the message is alcohol-related
def is_alcohol_related(message):
    if not message:
        return False
    return any(keyword in message.lower() for keyword in ALCOHOL_KEYWORDS)


# Helper: Generate image-based alcohol information
def generate_image_analysis(image_bytes):
    prompt = (
        "You're an expert alcohol identification assistant. Given this image of an alcohol bottle, "
        "return ONLY these 12 fields in this exact format using emojis. Write 'Not specified' if unknown.\n\n"
        "🔍 Identified alcohol:\n"
        "🌍 Origin:\n"
        "🍸 Alcohol Content:\n"
        "🌾 Main Ingredient:\n"
        "💅 Tasting Notes:\n"
        "🔹 Similar kind of alcohol (at least 3):\n"
        "🔗 Want to mix a cocktail? Try a recipe:\n"
        "✨ AI Bot Interactive Features:\n"
        "📊 Confidence Level:\n"
        "🏷 Brand Logo & History:\n"
        "🎥 YouTube Link:\n"
        "📦 Buy Online Link:\n"
        "🔄 Ask Again:"
    )

    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert alcohol assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                },
            ],
            temperature=0.3,
            max_tokens=700,
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error processing image: {str(e)}"


# Helper: Generate response for text query
def generate_text_response(message):
    if not is_alcohol_related(message):
        return "❌ This assistant only supports alcohol-related questions."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}],
            temperature=0.5,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error processing text: {str(e)}"


# API route
@app.route("/api/alcoholbot", methods=["POST"])
def alcoholbot():
    try:
        response_data = {}

        # Handle session ID
        session_id = request.form.get("session_id") or (
            request.json.get("session_id") if request.is_json else None
        )
        if session_id:
            session["session_id"] = session_id
        else:
            session["session_id"] = str(uuid.uuid4())

        # --- Handle Form-Data Image Upload ---
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(path)

            # Validate and process image
            try:
                image = Image.open(path).convert("RGB")
                byte_stream = io.BytesIO()
                image.save(byte_stream, format="JPEG")
                image_bytes = byte_stream.getvalue()

                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
                response_data["uploaded_image"] = f"/{path.replace(os.sep, '/')}"
            except Exception as e:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Image processing failed: {str(e)}",
                        }
                    ),
                    400,
                )
            finally:
                # Optional: Clean up uploaded file to save disk space
                if os.path.exists(path):
                    os.remove(path)

        # --- Handle JSON Base64 Image ---
        elif request.is_json and request.json.get("image_base64"):
            image_data = request.json["image_base64"]
            if "," in image_data:
                image_data = image_data.split(",")[1]
            try:
                image_bytes = base64.b64decode(image_data)
                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
            except Exception as e:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Base64 image processing failed: {str(e)}",
                        }
                    ),
                    400,
                )

        # --- Handle Text Message ---
        message = request.form.get("message") or (
            request.json.get("text") if request.is_json else None
        )
        if message:
            text_response = generate_text_response(message)
            response_data["text_response"] = text_response

        if not response_data:
            return jsonify({"success": False, "error": "No valid input provided."}), 400

        response_data["success"] = True
        response_data["session_id"] = session["session_id"]
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


# Run server
if __name__ == "__main__":
    app.run(debug=True)
