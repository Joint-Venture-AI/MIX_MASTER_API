import os
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Flask app and OpenAI client
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Prompt template
PROMPT = """
You are a professional bartender and drinks expert. Based ONLY on the image of an alcohol bottle I uploaded, generate a full cocktail or drink recipe in this exact visual structure and format:

---
[Alcohol Name]
Alcohol Content: [e.g., how much alcohol contains in the bottle]
Ingredient List: [List all ingredients used in the drink]
Flavor Profile: [Sweet/Bitter/Citrusy/etc.]
Drink Strength: [Light/Medium/Strong]
Glass Type: [e.g., Old-Fashioned, Highball, Margarita]

⭐ ratings all over the word(eg. 4.7/5) (how many reviews(eg. 10))

🔽 Servings: 4
🍳 Recipe: real Youtube Video Link of the alcohol bottle recipe

---

### Step - 01

Ingredients
| Ingredient       | ml  |
|------------------|-----|
| [Name]           | [XX]|
| ...              | ... |

---

Tastes Great With
🍗 [Dish 1]
🥗 [Dish 2]
🍲 Recipe

---

How to Make It
[Detailed drink preparation instructions here.]

---

### Step - 02
Prepare the Glass
- [Instruction 1]
📽️ *Visual Tip: [Tip here]*

---

### Step - 03
Mix the Ingredients
- [Instruction 1]
💡 *Tip: [Tip here]*

---

### Step - 04
Strain & Serve
- [Instruction 1]

---

### Step - 05
Garnish & Enjoy
- [Instruction 1]
🎥 *Optional: [Extra fun line]*

---

Only output the formatted recipe. Do not explain anything else.
"""


# Helper: Encode image to base64
def encode_image_to_base64(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")


# Endpoint: Upload bottle image and get recipe
@app.route("/generate_recipe", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No selected image."}), 400

    try:
        # Convert image to base64
        base64_image = encode_image_to_base64(image_file)

        # Send image and prompt to GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1200,
        )

        # Extract generated recipe
        result = response.choices[0].message.content
        return jsonify({"recipe": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run app
if __name__ == "__main__":
    app.run(debug=True)
