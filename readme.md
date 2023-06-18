# PyElectricity
Small basic recorder tool for gathering up electricity stats and storing them in a recording DB.

My setup consists of:
- `Fronius Symo Hybrid 5.0-3-S` (5kW inverter)
- `20x MaysunSolar 310Wp panels` (approx. 6kW peak effect)
- `Smart Meter 63A` (electricity meter)
- `Datalogger module` (logger/uploader to Fronius)
- `LG Resu H` (9800Wh battery)
- `PostgreSQL 13` (database running via Docker)
- `Raspberry Pi 3b+` (executing the scripts, runs Raspbian Linux)
- `Denver SHP-102` (SmartPlugs for recording energy consumption)

# Setup
There are several scripts that are queued and run individually:
- `solar_panels.py`, which will record data from the Fronius inverter and store it to a DB
- `power_prices.py`, which will grab power price data from Nordpool and store it to a DB
- `weather.py`, which will grab the weather forecast for your location from Openweathermap and store it to a DB
- `solcast.py`, which will grab the solar forecast from your home setup from [Solcast](https://toolkit.solcast.com.au/live-forecast) and store it to a DB
*make sure to create the DB tables first, there are creation scripts in the `sql` folder*

They're running in a Docker setup, and expect the following environment variables:
- `DB_HOST` - the database host
- `DB_PORT` - the database port
- `DB_USER` - the database username
- `DB` - the database
- `DB_PASS` - the database password
- `QUERY_FREQUENCY` - the query frequency for the intervert
- `THRESHOLD` - the threshold before a new query process is started (e.g. 60 when crontab scheduling every 5th minute)
- `INVERTERIP` - the inverter host
- `WEATHER_API` - the API key for [Openweather](https://openweathermap.org/api)
- `WEATHER_LAT` - the latitude to get the forecast for
- `WEATHER_LON` - the longitude to get the forecast for
- `SOLCAST_API` - the API key for [Solcast](https://docs.solcast.com.au/)
- `SOLCAST_SITE` - the Site reference for the solar setup at Solcast
- `DEVICEn_ID` - the device id of the nth [Tuya](https://iot.tuya.com/) smart plug; use [Network scanning](https://pypi.org/project/tinytuya/#:~:text=get%20these%20keys.-,Network%20Scanner,-TinyTuya%20has%20a) to obtain
- `DEVICEn_KEY` - the device key of the nth [Tuya](https://iot.tuya.com/) smart plug; use [Network scanning](https://pypi.org/project/tinytuya/#:~:text=get%20these%20keys.-,Network%20Scanner,-TinyTuya%20has%20a) to obtain

For example: 
```docker run --rm -d -e "DB_HOST=192.168.x.x" -e "DB_PORT=5432" -e "DB_USER=user" -e "DB=db" -e "DB_PASS=password" -e "QUERY_FREQUENCY=5" -e "THRESHOLD=60" -e "INVERTERIP=192.168.x.x" -e "WEATHER_API=457894" -e "WEATHER_LAT=12.3456" -e "WEATHER_LON=12.3456" -e "SOLCAST_API=657545" -e "SOLCAST_SITE=000a-b111-22c2-3d3d -e "DEVICE1_ID=123deviceID" -e"DEVICE1_KEY=123deviceKEY" -e "DEVICE2_ID=321deviceID" -e"DEVICE2_KEY=321deviceKEY" -e "DEVICE3_ID=456deviceID" -e"DEVICE3_KEY=456deviceKEY" -p 8501:8501 -p 6666-6667:6666-6667/udp -p 7000:7000/udp -p6668:6668/tcp pyelectricity```

The docker image is available on [Docker Hub](https://hub.docker.com/repository/docker/antra/pyelectricity/general).

# Visualising
Currently, I am using PowerBI for visualisation/dasboarding; I am not certain if that will be the permanent setup or if I should create some visualisations (e.g. as png) and embed to a website.
This is what it looks like at present.  

![powerbi dashboard](docs/sample_dashboard.png "Sample PowerBI dashboard")

## Basic dashboard
There's a basic dashboard added built with [Streamlit](https://streamlit.io/), it's accessible on `port 8501`.


# Historical sunrise/sunset
Fetched via the API available on [Sunrise Sunset](https://sunrise-sunset.org/api)

# Power consumption
Detailed power consumption, I record via [Tuya](https://iot.tuya.com/) compatible smart plugs.  
Some additional ports need to be forwarded to permit the [Network scanning](https://pypi.org/project/tinytuya/#:~:text=get%20these%20keys.-,Network%20Scanner,-TinyTuya%20has%20a) and find the devices without using the IoT cloud.  