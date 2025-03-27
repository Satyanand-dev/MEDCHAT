from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import google.generativeai as genai
import requests

app = Flask(__name__)
CORS(app, resources={r"/api/chat": {"origins": "*"}})

# Configure Gemini AI
GEMINI_API_KEY = "AIzaSyAsRZuKzLKZpHCd38x83x8olx66ao_DjQo"
genai.configure(api_key=GEMINI_API_KEY)

# Emergency Keywords
EMERGENCY_KEYWORDS = ["chest pain", "severe bleeding", "difficulty breathing", "unconscious", "heart attack", "stroke"]

# AI Prompt
CUSTOM_PROMPT = """Always respond in romanized text of the language the patient is speaking in.
You are a professional medical assistant.
Patients may describe their symptoms naturally in any language.
If their response is not concerned with medical issues, you may ask them to elaborate, strictly on medical issues.(important)
Recommend further actions or a visit to the doctor if need be
Offer further help after diagnosis
Respond in the following format:
Disease: I think that you may have <Disease>
<Explaination of why you think the patient has the disease>
<symptoms of the disease>
<Remedies>:
- Remedy 1
- Remedy 2
- Remedy 3 till 5"""

model = genai.GenerativeModel("gemini-2.0-flash-lite")

def get_nearby_hospitals(latitude, longitude):
    """Fetch nearby hospitals using OpenStreetMap's Nominatim API."""
    if not latitude or not longitude:
        return "❌ Location not provided. Unable to find hospitals."

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": "hospital",
        "format": "json",
        "limit": 3,
        "lat": latitude,
        "lon": longitude
    }

    print(f"🔍 Fetching hospitals from OpenStreetMap for location: {latitude}, {longitude}")
    response = requests.get(url, params=params)

    try:
        data = response.json()
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
        return "❌ Failed to retrieve hospital data."

    print(f"📩 OSM API Response: {data}")  # Debug log

    if data:
        hospitals = [f"🏥 {place['display_name']}" for place in data]
        return "\n".join(hospitals)

    return "❌ No hospitals found nearby."

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    """Handles chatbot requests and emergency detection."""

    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response, 200

    data = request.get_json()
    user_message = data.get("message", "").lower()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    print(f"📍 Received User Location: Latitude = {latitude}, Longitude = {longitude}")  # Debug log

    if not user_message:
        return jsonify({"reply": "❌ Please enter symptoms to proceed."}), 400

    # Detect Emergency
    is_emergency = any(keyword in user_message for keyword in EMERGENCY_KEYWORDS)

    # Create AI Prompt
    location_info = f"Patient's Location: {latitude}, {longitude}" if latitude and longitude else "Location not available"
    full_prompt = f"{CUSTOM_PROMPT}\n{location_info}\nPatient: {user_message}\nAI Response:"

    # Generate AI Response
    response = model.generate_content(full_prompt)

    if response and response.text:
        output = response.text.strip()
        formatted_response = f"🩺 {output}"

        # If emergency detected, fetch nearby hospitals
        if is_emergency:
            hospital_info = get_nearby_hospitals(latitude, longitude)
            formatted_response += f"\n\n🚨 **Emergency Detected!**\nPlease visit the nearest hospital:\n{hospital_info}"

        return jsonify({"reply": formatted_response})

    return jsonify({"reply": "❌ Unable to process your request. Please try again."})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
