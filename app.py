from flask import Flask, jsonify, request, send_file
import requests
import os
import urllib.request
from flask_cors import CORS  
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai

# Set up Gemini API key
genai.configure(api_key="YOUR_GEN_AI_API_KEY")

app = Flask(__name__, static_folder="static")
CORS(app)  

API_KEY = "GOOGLE_SHEETS_API_KEY"

# Mapping class & language selections to Google Sheets IDs
SHEET_MAP = {
    "class_9_english": "1MMs0_K62N4uN9cUK_tGeejuYXiwAqeHJ23Y63NnuA48",
    "class_9_hindi": "1b8tPbolv2LMUuUBbvPMQI8LNf0HYR1TqdLukQQAyG5Y",
    "class_10_english": "1VvZasWLzkREha_1RQSVHLyi6IEjI2dRztF_E4-8tqEI",
    "class_10_hindi": "1Mg3dKVvNqAokcVzxFdVUXTrsR4Ntg_boxC0wUaYJTT0"
}

def fetch_video_links(sheet_id):
    """ Fetch video links from Google Sheets API """
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:A10?key={API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises HTTP error if request fails
        data = response.json()
    except requests.exceptions.RequestException as e:
        print("API Error:", e)
        return {"error": "Failed to fetch data from Google Sheets"}

    links = [row[0] for row in data.get("values", []) if row and row[0].startswith("http")]

    # Extract YouTube Video IDs from URLs
    video_data = [{"url": link, "video_id": parse_qs(urlparse(link).query).get("v", [None])[0]} for link in links]

    return video_data if video_data else {"error": "No valid video links found"}

@app.route("/")
def home():
    """ Serve the navigation page (ed.html) as the default entry point """
    return send_file("static/nav.html")

@app.route("/videos", methods=["GET"])
def get_videos():
    """ Get video links based on selected class/language """
    class_language = request.args.get("class_language")

    if class_language not in SHEET_MAP:
        return jsonify({"error": "Invalid selection"}), 400

    sheet_id = SHEET_MAP[class_language]
    links = fetch_video_links(sheet_id)

    return jsonify({"video_links": links})

@app.route("/download", methods=["POST"])
def download_video():
    """ Handle video download requests """
    video_url = request.json.get("video_url")

    if not video_url or not video_url.endswith(".mp4"):
        return jsonify({"error": "Invalid video URL"}), 400

    filename = video_url.split("/")[-1]
    file_path = os.path.join("static/videos", filename)  # ✅ Store in static/videos

    try:
        urllib.request.urlretrieve(video_url, file_path)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/gemini-response", methods=["POST"])
def gemini_response():
    data = request.json
    user_query = data.get("query", "").strip()

    if not user_query:
        return jsonify({"answer": "I couldn't understand that. Please ask again."})

    selected_language = data.get("language", "English")  # Default: English
    response = get_gemini_response(user_query, selected_language)

    return jsonify({"answer": response})

def get_gemini_response(user_query,selected_language):
    """ Generate AI response using Gemini API with proper context """
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    prompt = f"Respond in an engaging and helpful way to this user query, Reply concisely in {selected_language} and Limit response to 10 lines or fewer. but also should be simple and more understanding. If asked anything outside of education or subject say, SORRY I CAN'T ASSIST WITH ANYTHING OUTSIDE EDUCATION: {user_query}"
    response = model.generate_content(prompt)
    
    return response.text if response.text else "I couldn't understand. Try rephrasing!"

if __name__ == "__main__":
    app.run(debug=True)
