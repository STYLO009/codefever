from flask import Flask, request, jsonify, render_template
from gennin_handler import ask_gemini  # Matches the existing function

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_input = data.get("message")
    bot_response = ask_gemini(user_input)
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    app.run(debug=True)
