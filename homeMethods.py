from flask import Flask, render_template, request, redirect, flash, session, url_for
import requests
from geopy.geocoders import Nominatim
from datetime import datetime
import random
from bs4 import BeautifulSoup




def get_weather_summary(location_geocoded, OWM_API_KEY):
    current_weather_json = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={location_geocoded.latitude}&lon={location_geocoded.longitude}&appid={OWM_API_KEY}&units=metric").json()

    weather_data = {
        'weather': current_weather_json['weather'][0]['description'],
        'temperature': current_weather_json['main']['temp'],
        'feels_like': current_weather_json['main']['feels_like'],
        'icon_url': f"http://openweathermap.org/img/wn/{current_weather_json['weather'][0]['icon']}@2x.png"
    }
    return weather_data


import requests
from datetime import datetime

def get_forecast(location_geocoded, WEATHERBIT_API_KEY):

    response = requests.get(
        f"https://api.weatherbit.io/v2.0/forecast/daily?lat={location_geocoded.latitude}&lon={location_geocoded.longitude}&key={WEATHERBIT_API_KEY}&days=7"
    )

    if response.status_code != 200:
        raise Exception(f"Error fetching forecast data: {response.status_code}")

    forecast_json = response.json()

    forecast = []

    for day in forecast_json['data']:

        date = datetime.strptime(day['valid_date'], "%Y-%m-%d").strftime("%A, %B %d, %Y")
        high_temp = day['max_temp']
        low_temp = day['min_temp']
        weather_desc = day['weather']['description']
        wind_speed = day['wind_spd']


        forecast.append({
            'date': date,
            'high_temp': high_temp,
            'low_temp': low_temp,
            'weather_desc': weather_desc,
            'wind_speed': wind_speed
        })


    return forecast




weather_comments = {
        "Rain": "if you so desire, consider an umbrella for your travels",
        "Clear": "Clear oh clear the skys are clear, might need sun cream",
        "Snow": "please do stay warm, the snow is frozen innit",
        "Thunderstorm": "dont be frightened by the thunderous storms",
        "Drizzle": "not raining that hard, you should be laughing",
        "Clouds": "It's a cloudy day, enjoy them whil they last",
    }

def get_today(forecast_data):
    today = forecast_data[0]
    return f"Today's weather: {today['weather_desc']}, High: {today['high_temp']}°C, Low: {today['low_temp']}°C."

def get_looking_ahead(forecast_data, day_index):
    try:
        day = forecast_data[day_index]
        return f"Looking ahead to {day['date']}: {day['weather_desc']}, High: {day['high_temp']}°C, Low: {day['low_temp']}°C."
    except IndexError:
        return "No forecast available for that date."


def get_location_image(location_name):
    access_key = "L1TbRmKHl1G9oGsATJRWYIcSB-065DSai0kF_yX4U-k"
    query = f"{location_name}"
    unsplash_url = f"https://api.unsplash.com/search/photos?page=1&query={query}&client_id={access_key}"


    try:
        response = requests.get(unsplash_url)
        response.raise_for_status()
        data = response.json()

        if data['results']:
            image_url = data['results'][0]['urls']['full']
            return image_url
        else:
            return "https://via.placeholder.com/1920x1080?text=City+Image+Not+Found"
    except Exception as e:
        print(f"Error fetching image: {e}")
        return "https://via.placeholder.com/1920x1080?text=Error+Loading+Image"