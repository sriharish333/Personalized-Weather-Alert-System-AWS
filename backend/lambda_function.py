from datetime import datetime, timezone, timedelta
import json
import urllib.parse
import urllib.request
import boto3

# --- CONFIGURATION ---
API_KEY = "ce7e549ee90406e847dfa62a95fee21b"

# Monitored locations (Cities & Countries)
CITIES = ["Chennai", "Delhi", "Switzerland", "Japan"]

# Verified sender email
SENDER_EMAIL = "sriharish7788@gmail.com"

# Verified team recipients
RECIPIENTS = [
    "sriharish7788@gmail.com",
    "srivarshini240207@gmail.com",
    "anbusurya2007@gmail.com",
]

# Region (Stockholm)
AWS_REGION = "eu-north-1"

ses_client = boto3.client("ses", region_name=AWS_REGION)


def get_coordinates(location):
    """Fetches latitude, longitude, weather data, and timezone offset for a location."""
    formatted_location = urllib.parse.quote(location)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={formatted_location}&appid={API_KEY}&units=metric"
    req = urllib.request.Request(url, headers={"User-Agent": "AWS-Lambda"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        resolved_name = data.get("name", location)
        timezone_offset = data.get("timezone", 0)  # Offset in seconds from UTC
        return (
            data["coord"]["lat"],
            data["coord"]["lon"],
            data["main"]["temp"],
            data["main"]["feels_like"],
            data["weather"][0]["description"].title(),
            data["weather"][0]["icon"],
            data["main"]["humidity"],
            data["wind"]["speed"],
            resolved_name,
            timezone_offset,
        )


def get_air_quality(lat, lon):
    """Fetches Air Quality Index and pollutants from OpenWeatherMap Air Pollution API."""
    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    req = urllib.request.Request(url, headers={"User-Agent": "AWS-Lambda"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        aqi_val = data["list"][0]["main"]["aqi"]
        components = data["list"][0]["components"]

        aqi_labels = {
            1: ("Good 🟢", "#22c55e"),
            2: ("Fair 🟡", "#eab308"),
            3: ("Moderate 🟠", "#f97316"),
            4: ("Poor 🔴", "#ef4444"),
            5: ("Very Poor 🟤", "#7f1d1d"),
        }
        aqi_text, aqi_color = aqi_labels.get(
            aqi_val, ("Unknown", "#64748b")
        )
        return aqi_text, aqi_color, components


def lambda_handler(event, context):
    city_cards_html = ""
    plain_text_lines = []
    alerts = []

    for loc in CITIES:
        try:
            (
                lat,
                lon,
                temp,
                feels_like,
                desc,
                icon_code,
                humidity,
                wind_spd,
                display_name,
                tz_offset,
            ) = get_coordinates(loc)

            # Calculate local time for the specific city/country
            local_time = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
            formatted_time = local_time.strftime("%A, %b %d %I:%M %p")

            aqi_text, aqi_color, components = get_air_quality(lat, lon)
            pm25 = components.get("pm2_5", 0)
            pm10 = components.get("pm10", 0)

            plain_text_lines.append(
                f"{display_name} ({formatted_time}): {temp}°C, {desc}, AQI: {aqi_text}"
            )

            # Customized Advisories & Direct Actions
            if "rain" in desc.lower() or "shower" in desc.lower() or "drizzle" in desc.lower():
                alerts.append(f"🌧️ <strong>{display_name}:</strong> Rain is expected! Keep umbrella with you before heading out.")

            if temp >= 38.0:
                alerts.append(f"🔥 <strong>{display_name}:</strong> Extreme heatwave ({temp}°C)! Stay indoors and keep hydrated.")
            elif temp <= 5.0:
                alerts.append(f"❄️ <strong>{display_name}:</strong> Freezing temperature ({temp}°C)! Wear heavy woolens.")

            if pm25 > 50.0:
                alerts.append(f"😷 <strong>{display_name}:</strong> Poor air quality detected (PM2.5: {pm25} µg/m³). Wear an N95 mask outdoors.")

            # Professional Highlighted City Card Layout with Place Name in Blue Badge
            city_cards_html += f"""
            <div style="background-color: #ffffff; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #cbd5e1;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td valign="middle">
                    <span style="background-color: #0284c7; color: #ffffff; font-size: 15px; font-weight: 800; text-transform: uppercase; padding: 6px 12px; border-radius: 6px; letter-spacing: 0.5px; display: inline-block; margin-bottom: 8px;">{display_name}</span>
                    <p style="margin: 4px 0 2px; color: #475569; font-size: 13px; font-weight: 500;">🕒 Local Time: {formatted_time}</p>
                    <p style="margin: 6px 0 0; color: #64748b; font-size: 15px;">{desc} &bull; <span style="color: #334155; font-weight: 500;">Feels like {feels_like}&deg;C</span></p>
                  </td>
                  <td align="right" valign="middle">
                    <img src="https://openweathermap.org/img/wn/{icon_code}@4x.png" width="75" height="75" alt="{desc}" style="display: block;">
                  </td>
                </tr>
              </table>
              <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 16px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="font-size: 14px; color: #334155;">
                <tr>
                  <td width="50%" style="padding: 6px 0;"><strong>🌡️ Temperature:</strong></td>
                  <td width="50%" style="padding: 6px 0; text-align: right; color: #0284c7; font-weight: 600;">{temp}&deg;C</td>
                </tr>
                <tr>
                  <td width="50%" style="padding: 6px 0;"><strong>💧 Humidity:</strong></td>
                  <td width="50%" style="padding: 6px 0; text-align: right; font-weight: 600;">{humidity}%</td>
                </tr>
                <tr>
                  <td width="50%" style="padding: 6px 0;"><strong>💨 Wind Speed:</strong></td>
                  <td width="50%" style="padding: 6px 0; text-align: right; font-weight: 600;">{wind_spd} m/s</td>
                </tr>
                <tr>
                  <td width="50%" style="padding: 6px 0;"><strong>😷 Air Quality (AQI):</strong></td>
                  <td width="50%" style="padding: 6px 0; text-align: right; color: {aqi_color}; font-weight: 600;">{aqi_text}</td>
                </tr>
                <tr>
                  <td width="50%" style="padding: 6px 0;"><strong>🌫️ PM2.5 / PM10:</strong></td>
                  <td width="50%" style="padding: 6px 0; text-align: right; font-weight: 600;">{pm25} / {pm10} µg/m³</td>
                </tr>
              </table>
            </div>
            """
        except Exception as e:
            plain_text_lines.append(f"{loc}: Error fetching data ({str(e)})")

    # Format Alert Banner Section
    if alerts:
        alerts_html = """
        <div style="background: #fef2f2; border-left: 5px solid #ef4444; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
          <strong style="color: #991b1b; font-size: 16px;">⚠️ Actionable Weather & Health Advisories</strong>
          <ul style="margin: 8px 0 0; padding-left: 20px; color: #b91c1c; font-size: 14px;">
        """
        for alert in alerts:
            alerts_html += f"<li style='margin-bottom: 6px;'>{alert}</li>"
        alerts_html += "</ul></div>"
    else:
        alerts_html = """
        <div style="background: #f0fdf4; border-left: 5px solid #22c55e; padding: 14px; border-radius: 8px; margin-bottom: 24px; color: #166534; font-size: 14px;">
          ✅ Perfect weather conditions across all monitored locations today. Safe travels!
        </div>
        """

    # Complete Clean Email Structure
    email_html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
      </head>
      <body style="margin: 0; padding: 30px 10px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 18px; overflow: hidden; border: 1px solid #cbd5e1; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
          <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 32px 24px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;">Global Weather & Advisory Digest</h1>
            <p style="color: #e0f2fe; margin: 8px 0 0; font-size: 15px;">Automated Serverless Intelligence via AWS Lambda & SES</p>
          </div>
          <div style="padding: 30px 24px; background-color: #f8fafc;">
            {alerts_html}
            {city_cards_html}
            <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #94a3b8;">
              Triggered automatically by Amazon EventBridge &bull; Powered by AWS Serverless
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    # Send email to the team via Amazon SES
    try:
        response = ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": RECIPIENTS},
            Message={
                "Subject": {
                    "Data": "🌍 Global Weather, Local Times & Priority Advisories"
                },
                "Body": {
                    "Text": {"Data": "\n".join(plain_text_lines)},
                    "Html": {"Data": email_html},
                },
            },
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Global digest with highlighted locations & directives sent successfully!"),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Failed to send email via SES: {str(e)}"),
        }
