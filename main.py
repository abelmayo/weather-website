from flask import Flask, render_template, request, redirect, flash, url_for, session
import requests
from geopy.geocoders import Nominatim
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from homeMethods import *
from flask import g
import re
from datetime import datetime
import pytz

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = "iguhdweibguhewfd"
OWM_API_KEY = "0797e32b0278766b686662803df493ed"
WEATHERBIT_API_KEY = "3870c6f4a70c4a24bbe1b6f2666dd4d2"
geolocator = Nominatim(user_agent="WeatherWebsite")
location_input = ""


#initializes the database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor(); 
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   email TEXT NOT NULL UNIQUE,
                   password TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS preferences (
                   user_id INTEGER,
                   temp_unit TEXT NOT NULL,
                   time_format BOOLEAN,
                   theme BOOLEAN TRUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS high_scores (
                   user_id INTEGER,
                   score INTEGER,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()


@app.route('/', methods=['GET', 'POST'])
def home():
    
    global location_input

    if 'user_id' not in session:
        flash('You are not logged in. Showing default weather.')
        location_input = location_input or "London" # Default to London if no input
    else:
        location_input = location_input or None

    if request.method == "POST":
        location_input = request.form.get("location", "").strip() or "London"

    try:
        location_geocoded = geolocator.geocode(location_input)
        if not location_geocoded:
            raise ValueError("Geocoding failed")
    except Exception as e:
        flash(f"Error finding location: {e}")
        location_geocoded = None

    if location_geocoded:
        try:
            # Fetch weather data using helper methods
            weather_summary = get_weather_summary(location_geocoded, OWM_API_KEY)
            forecast_data = get_forecast(location_geocoded, WEATHERBIT_API_KEY)

            today_summary = f"Today's weather: {forecast_data[0]['weather_desc']}, High: {forecast_data[0]['high_temp']}°C, Low: {forecast_data[0]['low_temp']}°C."
            looking_ahead_summary = f"Forecast for {forecast_data[1]['date']}: {forecast_data[1]['weather_desc']}, High: {forecast_data[1]['high_temp']}°C, Low: {forecast_data[1]['low_temp']}°C."
        except Exception as e:
            flash(f"Error retrieving weather data: {e}")
            weather_summary = {"weather": "N/A", "temperature": "N/A", "feels_like": "N/A", "icon_url": "/static/icons/default.png"}
            forecast_data = []
            today_summary = "N/A"
            looking_ahead_summary = "N/A"
    else:
        weather_summary = {"weather": "N/A", "temperature": "N/A", "feels_like": "N/A", "icon_url": "/static/icons/default.png"}
        forecast_data = []
        today_summary = "N/A"
        looking_ahead_summary = "N/A"

    # Fetch background image for location
    if location_geocoded:
        location_image_url = get_location_image(location_input)
    else:
        location_image_url = None


    print(location_geocoded) # Debugging print statement

    return render_template(
        "home.html",
        location=location_input,
        location_geocoded=location_geocoded.address if location_geocoded else "Location not found",
        weather=weather_summary["weather"],
        temperature=weather_summary["temperature"],
        feels_like=weather_summary["feels_like"],
        weather_summary = weather_summary,
        forecast=forecast_data,
        today_summary=today_summary,
        looking_ahead_summary=looking_ahead_summary,
        background_image=location_image_url,
        error=None if location_geocoded else "Location not found."
    )

    





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Input validation (email format)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            flash('Email format is invalid', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed_password))
                conn.commit()

            flash('Registration succesful, please log in')
            return redirect(url_for('login'))#change to the /thing default

        except sqlite3.IntegrityError:
            flash('email already exists')
            return render_template('register.html')
        
    return render_template('register.html')


#checks email and password against database
def authenticate_user(email, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email, password FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()

    conn.close()    
    print(result)
    if result and check_password_hash(result[3], password):
        return result
    else:
        return None

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = authenticate_user(email, password)

    #either access granted or error message
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
            return render_template('login.html')
        
    return render_template('login.html')

@app.before_request
def load_loggd_in_user():
    g.user_name = session.get('user_name')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'user_id' not in session:
        flash("Please log in to play the game.")
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(score) FROM high_scores WHERE user_id = ?", (user_id,))
    high_score = cursor.fetchone()[0] or 0
    conn.close()


    if request.method == 'POST':
        # Retrieve game state from the form
        user_guess = request.form.get("guess")
        current_temp = float(request.form.get("current_temp"))
        next_temp = float(request.form.get("next_temp"))
        current_city = request.form.get("current_city")
        next_city = request.form.get("next_city")
        current_image = request.form.get("current_image")
        next_image = request.form.get("next_image")

        score = int(request.form.get("score"))

        if (user_guess == "higher" and next_temp > current_temp) or (user_guess == "lower" and next_temp < current_temp):
            score += 1
            flash("Correct!")

            # Update the current city, temperature, and image
            current_city, current_temp, current_image = next_city, next_temp, next_image

            # Fetch new city's data
            try:
                next_city = random_city([current_city])
            except ValueError:
                next_city = random_city()
            
            next_temp, next_image = get_city_data(next_city, OWM_API_KEY)
            response = requests.get(next_temp)
            next_temp = response.json()["main"]["temp"]
        else:
            flash(f"Wrong! Your final score: {score}")
            save_high_score(session['user_id'], score)
            return redirect(url_for('game_over', score=score))
    else:
        # Initialize game state for a new game
        current_city = random_city()
        current_temp, current_image = get_city_data(current_city, OWM_API_KEY)
        response = requests.get(current_temp)
        current_temp = response.json()["main"]["temp"]

        next_city = random_city([current_city])
        next_temp, next_image = get_city_data(next_city, OWM_API_KEY)
        response = requests.get(next_temp)
        next_temp = response.json()["main"]["temp"]
        score = 0

    return render_template(
        "game.html",
        current_city=current_city,
        current_temp=current_temp,
        current_image=current_image,
        next_city=next_city,
        next_temp=next_temp,
        next_image=next_image,
        score=score,
        high_score=high_score
    )


@app.route('/game_over')
def game_over():
    #fetch scor from last game
    score = request.args.get("score", 0)
    return render_template("game_over.html", score=score)

def random_city(exclude=None):
    cities = [
        "London", "Paris", "Berlin", "Madrid", "Rome", "Brussels", "Vienna", "Warsaw",
        "Prague", "Budapest", "Bern", "Copenhagen", "Stockholm", "Helsinki", "Oslo",
        "Reykjavik", "Dublin", "Amsterdam", "Lisbon", "Bucharest", "Sofia", "Athens",
        "Ankara", "Moscow", "Beijing", "Tokyo", "Seoul", "New Delhi", "Bangkok",
        "Jakarta", "Manila", "Canberra", "Ottawa", "Washington D.C.", "Mexico City",
        "Brasilia", "Buenos Aires", "Santiago", "Pretoria", "Cairo", "Lagos", "Kinshasa",
        "Johannesburg", "Algiers", "Tripoli", "Tunis", "Khartoum", "Nairobi",
        "Cape Town", "Dakar", "Luanda", "Harare", "Accra", "Addis Ababa", "Rabat","Tel Aviv","Holders Hill","Jewish Free School","Jerusalem","Haifa","Eilat","Antartica",
    ]
    if exclude:
        cities = [city for city in cities if city not in exclude]

    if not cities:
        raise ValueError("No cities left to choose from.")
    
    return random.choice(cities)


def get_city_data(city, OWM_API_KEY):
    temp = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OWM_API_KEY}&units=metric"
    image = get_location_image(city)
    print(f"City: {city}, Image URL: {image}")
    return temp, image

def save_high_score(user_id, score):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO high_scores (user_id, score) VALUES (?, ?)",
            (user_id, score)
        )
        conn.commit()


@app.route('/leaderboard')
def leaderboard():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT u.name, MAX(h.score) as best_score, MAX(h.created_at) as latest_attempt
    FROM high_scores h
    JOIN users u ON u.id = h.user_id
    GROUP BY u.id
    ORDER BY best_score DESC, latest_attempt ASC
''')

    leaderboard_data = cursor.fetchall()
    conn.close()

    return render_template('leaderboard.html', leaderboard=leaderboard_data, enumerate=enumerate)



@app.route('/compare', methods=['GET', 'POST'])
def compare():
    
    #initializ the list of locations in session if doesnt exist
    if 'locations_to_compare' not in session:
        session['locations_to_compare'] = []
        print("Initializd 'locations_o_compare' in session") #debugging
    
    if request.method == 'POST':
        # Check if user wants to clear the list
        if 'clear' in request.form:
            session['locations_to_compare'] = []
            print("Cleared all locations from the session.")  # Debugging
        else:
            # Add new location to the list
            location = request.form.get('locations', '').strip()
            if location:
                data = get_detailed_weather(location)  # Validate location first
                if data:
                    if location not in session['locations_to_compare']:  # Prevent duplicates
                        session['locations_to_compare'].append(location)
                        flash(f"Added {location}.", "success")
                else:
                    flash("Invalid location. Please enter a valid city name.", "error")

        # Mark session as modified to ensure changes are saved
        session.modified = True

    # Fetch weather data for all locations in the session
    weather_data = []
    for location in session.get('locations_to_compare', []):
        data = get_detailed_weather(location)
        if data:
            weather_data.append(data)
            print(f"Weather data fetched for: {location}")  # Debugging
        else:
            print(f"Failed to fetch weather data for: {location}")  # Debugging

            

    # Render the template with the list of locations and weather data
    return render_template(
        "compare.html",
        locations=session.get('locations_to_compare', []),
        weather_data=weather_data
    )


def get_detailed_weather(location):

    try:
        # geocode location to get coordinates
        location_geocoded = geolocator.geocode(location)
        if not location_geocoded:
            return None

        # fetch weather data
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={location_geocoded.latitude}&lon={location_geocoded.longitude}&appid={OWM_API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status() # error  for bad response
        weather_data = response.json()

        # Convert Unix timestamps to readable time
        timezone_offset = weather_data['timezone']  # Offset in seconds
        local_tz = pytz.FixedOffset(timezone_offset // 60)

        sunrise_time = datetime.utcfromtimestamp(weather_data['sys']['sunrise']).replace(tzinfo=pytz.utc).astimezone(local_tz)
        sunset_time = datetime.utcfromtimestamp(weather_data['sys']['sunset']).replace(tzinfo=pytz.utc).astimezone(local_tz)


        return {
            'location': location,
            'temperature': weather_data['main']['temp'],
            'feels_like': weather_data['main']['feels_like'],
            'humidity': weather_data['main']['humidity'],
            'wind_speed': weather_data['wind']['speed'],
            'pressure': weather_data['main']['pressure'],
            'visibility': weather_data.get('visibility', 'N/A'),
            'sunrise': sunrise_time.strftime('%H:%M %p'),  # Converts to HH:MM AM/PM
            'sunset': sunset_time.strftime('%H:%M %p'),
            'weather_description': weather_data['weather'][0]['description'],
            'icon': weather_data['weather'][0]['icon'],
            'cloud_coverage': weather_data['clouds']['all'],
            'precipitation': weather_data.get('rain', {}).get('1h', 0) + weather_data.get('snow', {}).get('1h', 0),
        }

    except Exception as e:
        print(f"Error fetching weather data for {location}: {e}")
        return None


if __name__ == "__main__":
    app.run(port=5000)