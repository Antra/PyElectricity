from config import setup_logger, get_engine, weather_api_key, latitude, longitude, TIME_FORMAT
import requests
import pandas as pd


logger = setup_logger('Weather', level='INFO')
logger.info('*** PyElectricity: Weather starting ***')

API_BASE_URL = 'api.openweathermap.org'


def get_weather_data(API_BASE_URL, weather_api_key, latitude, longitude):
    exclude = 'minutely'
    units = 'metric'
    url = f'https://{API_BASE_URL}/data/2.5/onecall?lat={latitude}&lon={longitude}&exclude={exclude}&units={units}&appid={weather_api_key}'
    try:
        response = requests.get(url).json()
        if response:
            current_weather = pd.DataFrame(data=response['current'])
            timezone = response['timezone']
            for col in ['dt', 'sunrise', 'sunset']:
                current_weather[col] = pd.to_datetime(
                    current_weather[col], unit='s').dt.tz_localize('UTC').dt.tz_convert(timezone)
            current_weather = pd.concat([current_weather.drop(['weather'], axis=1),
                                         current_weather['weather'].apply(pd.Series)], axis=1)

            hourly = pd.DataFrame(data=response['hourly'])
            hourly['dt'] = pd.to_datetime(hourly['dt'], unit='s').dt.tz_localize(
                'UTC').dt.tz_convert(timezone)
            hourly = pd.concat(
                [hourly.drop(['weather'], axis=1),
                 pd.DataFrame(hourly.weather.tolist(), index=hourly.index)[
                    0].apply(pd.Series)
                 ], axis=1)
            if 'rain' in hourly.columns:
                hourly = pd.concat(
                    [hourly.drop(['rain'], axis=1),
                     hourly['rain'].apply(pd.Series)], axis=1).rename(columns={'1h': 'rain'}).drop(columns=0).fillna({'rain': 0})
            if 'snow' in hourly.columns:
                hourly = pd.concat(
                    [hourly.drop('snow', axis=1),
                     hourly['snow'].apply(pd.Series)
                     ], axis=1).rename(columns={'1h': 'snow'}).drop(columns=0).fillna({'snow': 0})
            daily = pd.DataFrame(data=response['daily'])
            for col in ['dt', 'sunrise', 'sunset', 'moonrise', 'moonset']:
                daily[col] = pd.to_datetime(daily[col], unit='s').dt.tz_localize(
                    'UTC').dt.tz_convert(timezone)
            daily = pd.concat(
                [daily.drop(['weather', 'temp', 'feels_like'], axis=1),
                 pd.DataFrame(daily.weather.tolist(), index=daily.index)[
                    0].apply(pd.Series),
                 daily['temp'].apply(pd.Series),
                 daily['feels_like'].apply(pd.Series)], axis=1).set_index(daily['dt'].dt.date).drop(columns=['dt'])
            daily.index = pd.to_datetime(daily.index)
            logger.debug(
                f"Weather: Fetched some data from the weather API: {response['current']}")
            return current_weather, hourly, daily
    except Exception as err:
        logger.error(
            f'** Weather: Error getting data from the weather API! Error message: {err}')


def store_basic_info(df):
    try:
        engine = get_engine()
        # delete existing values
        delete_query = f"""DELETE FROM weather_sunrise WHERE date IN {tuple(df.index.strftime('%Y-%m-%d'))}"""
        with engine.connect() as conn:
            conn.execute(delete_query)
        df[['sunrise', 'sunset']].to_sql('weather_sunrise', engine, if_exists='append',
                                         index=True, index_label='date')
    except Exception as err:
        logger.error(
            f'** Weather: Error writing sunrise data to DB! Error message: {err}')


def store_hourly_forecast(df):
    try:
        engine = get_engine()
        # delete existing values
        delete_query = f"""DELETE FROM weather_hourly WHERE date IN {tuple(df.index.strftime(TIME_FORMAT))}"""
        with engine.connect() as conn:
            conn.execute(delete_query)
        df.to_sql('weather_hourly', engine, if_exists='append',
                  index=True, index_label='date')
    except Exception as err:
        logger.error(
            f'** Weather: Error writing hourly forecast data to DB! Error message: {err}')


# get the weather data
current_weather, hourly_forecast, daily_forecast = get_weather_data(
    API_BASE_URL, weather_api_key, latitude, longitude)


# map the sunrise/sunset to the hourly forecast
hourly_forecast[['sunrise', 'sunset']] = hourly_forecast['dt'].dt.date.map(
    daily_forecast[['sunrise', 'sunset']].to_dict(orient='index')).apply(pd.Series)
hourly_forecast['during_day'] = False
hourly_forecast.loc[(hourly_forecast.dt.dt.time >= hourly_forecast.sunrise.dt.time) & (
    hourly_forecast.dt.dt.time <= hourly_forecast.sunset.dt.time), 'during_day'] = True
hourly_forecast.drop(columns=['sunrise', 'sunset'],
                     inplace=True)
hourly_forecast.set_index('dt', inplace=True)

# write it do the database
store_basic_info(daily_forecast)
store_hourly_forecast(hourly_forecast)


logger.info('*** PyElectricity: Weather terminating ***')
