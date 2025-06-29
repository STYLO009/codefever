
from flask import Flask, render_template
import requests

app = Flask(__name__)

API_KEY = "b49e83689dca43d08d274701251706"  # Replace with your actual key

def get_location():
    # Example fixed location (you can enhance with IP-based detection)
    return "London"

def get_weather(city):
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}&aqi=no"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.route('/')
def home():
    city = get_location()
    weather_data = get_weather(city)
    return render_template("home.html", weather=weather_data, city=city)

if __name__ == '__main__':
    app.run(debug=True)
