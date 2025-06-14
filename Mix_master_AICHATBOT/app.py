from flask import Flask, request, jsonify, session
from werkzeug.utils import secure_filename
import os
import io
import uuid
import base64
from PIL import Image
import openai

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Set your OpenAI API key here or set environment variable OPENAI_API_KEY
openai.api_key = os.getenv("OPENAI_API_KEY") or "your_openai_api_key_here"


# Helpers
def save_message(role, message, source="text"):
    print(f"Saved message from {role}: {message} (source: {source})")


def load_chat_history():
    # You can expand this to keep track of chat history per session if needed
    return []


def remove_duplicates(text):
    # You can enhance this function to clean repeated texts if necessary
    return text


def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def generate_image_analysis(image_bytes):
    prompt = (
        "You're an expert bottle identification assistant. Please strictly return ONLY these 12 details in this exact format, using emojis, without any extra sentences. If a field is unknown, write 'Not specified'.\n\n"
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

    # Convert image bytes to base64 string for embedding if needed (OpenAI's text models don't handle images)
    # But OpenAI's GPT-4 Vision or image understanding models require special API calls, not yet public.
    # For now, we'll encode image as base64 and pass it in prompt (or you may want to use external vision APIs).

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # Compose the message for chat completion
    messages = [
        {
            "role": "system",
            "content": "You are an expert assistant for bottle identification.",
        },
        {
            "role": "user",
            "content": prompt + "\n\nImage data (base64): " + image_base64,
        },
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # or "gpt-4" if you have access, adjust accordingly
        messages=messages,
        temperature=0.3,
        max_tokens=500,
        n=1,
    )
    return remove_duplicates(response.choices[0].message["content"])


@app.route("/api/unified", methods=["POST"])
def api_unified():
    try:
        response_data = {}
        session_id = (
            request.form.get("session_id") or request.json.get("session_id")
            if request.is_json
            else None
        )
        if session_id:
            session["session_id"] = session_id

        # Handle text input
        message = request.form.get("message") or (
            request.json.get("text") if request.is_json else None
        )
        if message:
            save_message("user", message)
            history = load_chat_history()

            # Construct conversation history for OpenAI chat completion
            messages = [
                {"role": msg["role"], "content": msg["message"]} for msg in history
            ]
            messages.append({"role": "user", "content": message})

            response = openai.ChatCompletion.create(
                model="gpt-4",  # or "gpt-4"
                messages=messages,
                temperature=0.7,
                max_tokens=300,
                n=1,
            )
            cleaned_text = remove_duplicates(response.choices[0].message["content"])
            save_message("model", cleaned_text)
            response_data["text_response"] = cleaned_text

        # Handle image input
        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(path)

            image = Image.open(path).convert("RGB")
            byte_stream = io.BytesIO()
            image.save(byte_stream, format="JPEG")
            image_bytes = byte_stream.getvalue()

            cleaned_image = generate_image_analysis(image_bytes)
            uploaded_image_url = f"/{path.replace(os.sep, '/')}"
            save_message("model", cleaned_image, source="image")
            response_data["image_response"] = cleaned_image
            response_data["uploaded_image"] = uploaded_image_url

        elif request.is_json:
            image_data = request.json.get("image_base64")
            if image_data:
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                cleaned_image = generate_image_analysis(image_bytes)
                save_message("model", cleaned_image, source="image")
                response_data["image_response"] = cleaned_image

        if (
            "text_response" not in response_data
            and "image_response" not in response_data
        ):
            return jsonify({"error": "No valid input provided"}), 400

        response_data["session_id"] = get_session_id()
        response_data["success"] = True
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == "__main__":
    app.run(debug=True)
