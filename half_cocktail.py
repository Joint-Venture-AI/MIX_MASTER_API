import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
#fuck it

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


# Helper: Encode image to base64
def encode_image_to_base64(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")


# Updated Prompt Template
INSTRUCTION_PROMPT = """
You are a professional bartender and drinks expert. Based ONLY on the image of the alcohol bottle AND the provided cocktail form information, write ONLY the steps starting from:

---

How to Make It
[Detailed drink preparation instructions here.]

---

### Step - 02
Prepare the Glass
- [Instruction 1]
- [Instruction 2]
- [Instruction 3]
📽️ *Visual Tip: [Tip here]*

---

### Step - 03
Mix the Ingredients
- [Instruction 1]
- [Instruction 2]
- [Instruction 3]
💡 *Tip: [Tip here]*

---

### Step - 04
Strain & Serve
- [Instruction 1]
- [Instruction 2]
- [Instruction 3]

---

### Step - 05
Garnish & Enjoy
- [Instruction 1]
- [Instruction 2]
- [Instruction 3]
🎥 *Optional: [Extra fun line]*

---

Use the information below from the form:

Name: {name}
Category: {category}
Alcohol Content: {alcohol_content}
Drink Strength: {drink_strength}
Glass Type: {glass_type}
Servings: {servings}

Ingredients:
{ingredients}

Description: {description}

Only output from “How to Make It” onward. Do not explain anything else.
"""


# Endpoint
@app.route("/generate_recipe", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No selected image."}), 400

    try:
        # Get form data
        name = request.form.get("name", "")
        category = request.form.get("category", "")
        alcohol_content = request.form.get("alcohol_content", "")
        drink_strength = request.form.get("drink_strength", "")
        glass_type = request.form.get("glass_type", "")
        servings = request.form.get("servings", "")
        description = request.form.get("description", "")

        # Dynamically collect ingredients
        ingredients = ""
        for key in request.form:
            if key.startswith("ingredient_"):
                ing_name = request.form.get(key)
                qty_key = key.replace("ingredient_", "quantity_")
                qty = request.form.get(qty_key, "")
                if ing_name:
                    ingredients += f"- {ing_name}: {qty} ml\n"

        # Prepare the dynamic prompt
        filled_prompt = INSTRUCTION_PROMPT.format(
            name=name,
            category=category,
            alcohol_content=alcohol_content,
            drink_strength=drink_strength,
            glass_type=glass_type,
            servings=servings,
            ingredients=ingredients.strip(),
            description=description,
        )

        # Convert image to base64
        base64_image = encode_image_to_base64(image_file)

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": filled_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )

        result = response.choices[0].message.content
        return jsonify({"recipe": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run app
if __name__ == "__main__":
    app.run(debug=True)
