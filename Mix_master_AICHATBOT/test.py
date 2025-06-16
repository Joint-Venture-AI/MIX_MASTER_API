import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
import base64

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/image-details", methods=["POST"])
def image_details():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        # Using new API for chat completion
        response = openai.chat.completions.create(
            model="gpt-4o",  # Replace with your vision-enabled GPT-4 model if you have access
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that describes images.",
                },
                {
                    "role": "user",
                    "content": "Describe the content of this image in detail.",
                },
                {"role": "user", "content": f"<image>{image_base64}</image>"},
            ],
        )

        description = response.choices[0].message.content
        return jsonify({"description": description})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
