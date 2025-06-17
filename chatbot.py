import os
import io
import uuid
import base64
import pymysql
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Flask setup
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Database connection helper
def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


# Allowed alcohol keywords
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


# Check if message is alcohol-related
def is_alcohol_related(message):
    if not message:
        return False
    return any(keyword in message.lower() for keyword in ALCOHOL_KEYWORDS)


# Save a chat message to DB
def save_message(session_id, message_type, content):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_history (session_id, message_type, content) VALUES (%s, %s, %s)",
                (session_id, message_type, content),
            )
    finally:
        conn.close()


# Retrieve full chat history by session_id, oldest first
def get_chat_history(session_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT message_type, content FROM chat_history WHERE session_id = %s ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "role": "user" if row["message_type"] == "user" else "assistant",
                    "content": row["content"],
                }
                for row in rows
            ]
    finally:
        conn.close()


# Clear chat history endpoint
@app.route("/api/alcoholbot/clear", methods=["POST"])
def clear_history():
    session_id = request.json.get("session_id")
    if not session_id:
        return jsonify({"success": False, "error": "session_id required"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM chat_history WHERE session_id = %s", (session_id,)
            )
    finally:
        conn.close()
    return jsonify({"success": True, "message": "Chat history cleared."})


# Generate image analysis response from OpenAI
def generate_image_analysis(image_bytes):
    prompt = (
        "You are an expert alcohol identification assistant. "
        "Analyze the given image of an alcohol bottle. Provide answers ONLY in this exact format with emojis:\n\n"
        "🔍 Identified alcohol: <name or 'Not specified'>\n"
        "🌍 Origin: <origin or 'Not specified'>\n"
        "🍸 Alcohol Content: <percentage or 'Not specified'>\n"
        "🌾 Main Ingredient: <ingredient or 'Not specified'>\n"
        "💅 Tasting Notes: <notes or 'Not specified'>\n"
        "🔹 Similar kind of alcohol (at least 3): <list or 'Not specified'>\n"
        "🔗 Want to mix a cocktail? Try a recipe: <recipe or 'Not specified'>\n"
        "✨ AI Bot Interactive Features: <features or 'Not specified'>\n"
        "📊 Confidence Level: <0-100% or 'Not specified'>\n"
        "🏷 Brand Logo & History: <info or 'Not specified'>\n"
        "🎥 YouTube Link: <link or 'Not specified'>\n"
        "📦 Buy Online Link: <link or 'Not specified'>\n"
        "🔄 Ask Again: <encourage user to ask again or 'Not specified'>\n\n"
        "If you are not sure about any field, write 'Not specified'."
    )
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
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
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error processing image: {str(e)}"


# Generate text reply including full chat history
def generate_text_response(session_id, message):
    if not is_alcohol_related(message):
        return "❌ This assistant only supports alcohol-related questions."

    # Retrieve chat history for context
    history = get_chat_history(session_id)
    history.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            temperature=0.5,
            max_tokens=500,
        )
        reply = response.choices[0].message.content.strip()
        # Save messages to DB
        save_message(session_id, "user", message)
        save_message(session_id, "assistant", reply)
        return reply
    except Exception as e:
        return f"Error processing text: {str(e)}"


# Main API endpoint
@app.route("/api/alcoholbot", methods=["POST"])
def alcoholbot():
    try:
        response_data = {}

        # Get or generate session_id
        session_id = (
            request.form.get("session_id")
            or (request.json.get("session_id") if request.is_json else None)
            or str(uuid.uuid4())
        )

        # Handle image uploaded via form-data
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(path)

            try:
                image = Image.open(path).convert("RGB")
                byte_stream = io.BytesIO()
                image.save(byte_stream, format="JPEG")
                image_bytes = byte_stream.getvalue()

                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
                response_data["uploaded_image"] = f"/{path.replace(os.sep, '/')}"
                save_message(session_id, "user", "[Image Uploaded]")
                save_message(session_id, "assistant", image_response)
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
                if os.path.exists(path):
                    os.remove(path)

        # Handle image via JSON base64
        elif request.is_json and request.json.get("image_base64"):
            image_data = request.json["image_base64"]
            if "," in image_data:
                image_data = image_data.split(",")[1]
            try:
                image_bytes = base64.b64decode(image_data)
                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
                save_message(session_id, "user", "[Image Base64]")
                save_message(session_id, "assistant", image_response)
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

        # Handle text message
        message = request.form.get("message") or (
            request.json.get("text") if request.is_json else None
        )
        if message:
            text_response = generate_text_response(session_id, message)
            response_data["text_response"] = text_response

        if not response_data:
            return jsonify({"success": False, "error": "No valid input provided."}), 400

        response_data["success"] = True
        response_data["session_id"] = session_id

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
