import os
import openai
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Flask app
app = Flask(__name__)
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def search_serper(query):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 3}
    res = requests.post(url, json=payload, headers=headers)
    return res.json()


def generate_prompt(brand_name, description, serper_data):
    snippets = "\n".join(
        [item.get("snippet", "") for item in serper_data.get("organic", [])]
    )
    return f"""
You are a professional alcohol brand assistant and cocktail recipe formatter.

I will give you a brand name and a short description. Using the description, and any additional web search insights, you will return a **stylized, emoji-rich, multi-step output** in the following **EXACT format**:

----------------------
Brand Name: {brand_name}
Alcohol Content: [write here like '30%']
Flavor Profile: [e.g., Spicy, Bold]
Cocktail Strength: [e.g., Medium]
(real number Votes, real number of Reviews)

⭐⭐⭐⭐⭐(based on real rating)

🔁 Serving  📹 Recipe

Step 01
Ingredients

Vodka                     [ml]

Coffee liqueur                [ml]

Lemon juice                 [ml]

Tastes Great With

Food Iteam 1

Food Iteam 2

Food Iteam 3

How to Make it
[Describe how to mix ingredients in a classy cocktail way, add emojis where needed]

Step 02
Prepare the Glass

[Instructions to chill or prep the glass, use formatting shown above in bold dots]

Step 03
Mix the Ingredients

[Explain how to shake, stir, and strain with details in bold dots]

Step 04
Strain & Serve

[Finishing touches, include texture or foam if needed in bold dots]

Step 05
Garnish & Enjoy

[How to garnish, smiley emojis and fun tone]

----------------------

Brand name: {brand_name}
Description: {description}

Extra info from web (if useful):
{snippets}

Now return only the formatted output in the exact structure above. Do not explain anything outside the format.
"""


@app.route("/alcohol-info", methods=["POST"])
def alcohol_info():
    try:
        brand_name = request.form.get("brand_name")
        description = request.form.get("description")
        image = request.files.get("image")  # Optional, not used in this version

        if not brand_name or not description:
            return jsonify({"error": "brand_name and description are required."}), 400

        # Step 1: Search for related info
        serper_data = search_serper(brand_name)

        # Step 2: Construct the formatted prompt
        prompt = generate_prompt(brand_name, description, serper_data)

        # Step 3: Get OpenAI completion
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a knowledgeable cocktail expert.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )

        result_text = response.choices[0].message.content.strip()
        return jsonify({"result": result_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
