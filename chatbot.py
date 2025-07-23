import os
import io
import uuid
import base64
import pymysql
import logging
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
from database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load .env variables
load_dotenv()

# Flask setup
app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Verify upload folder permissions
try:
    test_file = os.path.join(app.config["UPLOAD_FOLDER"], "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    logging.info("Upload folder is writable")
except Exception as e:
    logging.error(f"Upload folder permission error: {str(e)}")

# OpenAI client
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    logging.info("OpenAI client initialized")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {str(e)}")


# Serve frontend
@app.route("/")
def serve_html():
    return send_file("chatbot.html")

@app.route("/chatbot.html")
def serve_chatbot():
    return send_file("chatbot.html")


# Serve static uploads
@app.route("/static/uploads/<path:filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Health check endpoint
@app.route("/api/health")
def health_check():
    return jsonify({"status": "healthy", "service": "Mix Master AI"})

# Analytics endpoint
@app.route("/api/analytics")
def get_analytics():
    try:
        analytics = db_manager.get_analytics()
        return jsonify({"success": True, "analytics": analytics})
    except Exception as e:
        logging.error(f"Analytics error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Session stats endpoint
@app.route("/api/session/<session_id>/stats")
def get_session_stats(session_id):
    try:
        stats = db_manager.get_session_stats(session_id)
        if stats:
            return jsonify({"success": True, "stats": stats})
        else:
            return jsonify({"success": False, "error": "Session not found"}), 404
    except Exception as e:
        logging.error(f"Session stats error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Database connection helper
def get_db():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        logging.info("Database connection established")
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise


# Check if message or previous message is relevant
def is_alcohol_related(message, session_id):
    if not message:
        return False
    return True


# Save a chat message to DB
def save_message(session_id, message_type, content):
    return db_manager.save_message(session_id, message_type, content)


# Retrieve full chat history by session_id, oldest first
def get_chat_history(session_id):
    return db_manager.get_chat_history(session_id)


# Clear chat history endpoint
@app.route("/api/alcoholbot/clear", methods=["POST"])
def clear_history():
    session_id = request.json.get("session_id")
    if not session_id:
        logging.error("Clear history failed: session_id required")
        return jsonify({"success": False, "error": "session_id required"}), 400

    try:
        success = db_manager.clear_chat_history(session_id)
        if success:
            return jsonify({"success": True, "message": "Chat history cleared."})
        else:
            return jsonify({"success": False, "error": "Failed to clear history"}), 500
    except Exception as e:
        logging.error(f"Clear history error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Generate image analysis response from OpenAI
def generate_image_analysis(image_bytes):
    prompt = (
        "You are an expert identification assistant. "
        "Analyze the given image. Provide answers ONLY in this exact format with emojis:\n\n"
        "🔍 Identified item: <name or 'Not specified'>\n"
        "🌍 Origin: <origin or 'Not specified'>\n"
        "🍸 Content: <percentage or 'Not specified'>\n"
        "🌾 Main Ingredient: <ingredient or 'Not specified'>\n"
        "💅 Notes: <notes or 'Not specified'>\n"
        "🔹 Similar items (at least 3): <list or 'Not specified'>\n"
        "🔗 Want to use it? Try a suggestion: <suggestion or 'Not specified'>\n"
        "🔄 Ask Again: <encourage user to ask again or 'Not specified'>\n\n"
        "If you are not sure about any field, write 'Not specified'."
    )
    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        logging.info("Image encoded to base64")

        messages = [
            {"role": "system", "content": "You are an expert assistant."},
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

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=700,
        )
        logging.info("Image analysis response received from OpenAI")
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Image analysis failed: {str(e)}")
        return f"Error processing image: {str(e)}"


# Generate text response with last 5 messages
def generate_text_response(session_id, message):
    if not is_alcohol_related(message, session_id):
        logging.info(f"Message '{message}' accepted")
        return "❌ Sorry, I couldn't process that! Try asking something else. 🍷"

    full_history = get_chat_history(session_id)
    full_history.append({"role": "user", "content": message})
    limited_history = full_history[-5:]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly, expert assistant. "
                        "Respond in 2-3 concise sentences with a conversational tone. "
                        "Encourage follow-up questions with a prompt like '🍹 Got another question?'"
                    ),
                },
                *limited_history,
            ],
            temperature=0.5,
            max_tokens=100,
        )
        reply = response.choices[0].message.content.strip()
        logging.info(f"Text response generated: {reply[:50]}...")
        save_message(session_id, "user", message)
        save_message(session_id, "assistant", reply)
        return reply
    except Exception as e:
        logging.error(f"Text processing failed: {str(e)}")
        return f"Error processing text: {str(e)}"


# Main API endpoint
@app.route("/api/alcoholbot", methods=["POST"])
def alcoholbot():
    try:
        response_data = {}
        session_id = (
            request.form.get("session_id")
            or (request.json.get("session_id") if request.is_json else None)
            or str(uuid.uuid4())
        )
        logging.info(f"Processing request for session {session_id}")

        # Handle image via form-data
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            logging.info(f"Saving image to {path}")
            try:
                image_file.save(path)
                image = Image.open(path).convert("RGB")
                byte_stream = io.BytesIO()
                image.save(byte_stream, format="JPEG")
                image_bytes = byte_stream.getvalue()
                logging.info("Image processed successfully")

                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
                response_data["uploaded_image"] = f"/{path.replace(os.sep, '/')}"
                save_message(session_id, "user", "[Image Uploaded]")
                save_message(session_id, "assistant", image_response)
            except Exception as e:
                logging.error(f"Image processing failed: {str(e)}")
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
                    logging.info(f"Deleted temporary image file {path}")

        # Handle image via JSON base64
        elif request.is_json and request.json.get("image_base64"):
            image_data = request.json["image_base64"]
            logging.info("Processing base64 image")
            if "," in image_data:
                image_data = image_data.split(",")[1]
            try:
                image_bytes = base64.b64decode(image_data)
                image_response = generate_image_analysis(image_bytes)
                response_data["image_response"] = image_response
                save_message(session_id, "user", "[Image Base64]")
                save_message(session_id, "assistant", image_response)
            except Exception as e:
                logging.error(f"Base64 image processing failed: {str(e)}")
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
            logging.error("No valid input provided")
            return jsonify({"success": False, "error": "No valid input provided."}), 400

        response_data["success"] = True
        response_data["session_id"] = session_id
        logging.info(f"Response sent for session {session_id}")
        return jsonify(response_data)

    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
