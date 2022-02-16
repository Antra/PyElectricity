from datetime import timedelta
from config import setup_logger, get_engine, solcast_api_key, solcast_site, TIME_FORMAT
import requests
import pandas as pd

logger = setup_logger('Solcast', level='INFO')
logger.info('*** PyElectricity: Solcast starting ***')

API_BASE_URL = 'api.solcast.com.au'


def get_solcast_data(API_BASE_URL, api_key, site_id):
    url = f'https://{API_BASE_URL}/rooftop_sites/{site_id}/forecasts?format=json'
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers).json()
        if response:
            solar_forecast = pd.DataFrame(data=response['forecasts'])
            solar_forecast['period_end'] = pd.to_datetime(
                solar_forecast['period_end'])
            # period is specified as PT30M; so getting the start period to be consistent
            solar_forecast['timestamp'] = pd.to_datetime(
                solar_forecast['period_end']) - timedelta(minutes=30)
            solar_forecast.set_index('timestamp', inplace=True)
            solar_forecast.drop(columns=['period_end', 'period'], inplace=True)

            logger.debug(
                f"Solcast: Fetched some data from the Solcast API: {response}")
            return solar_forecast
    except Exception as err:
        logger.error(
            f'** Solcast: Error getting data from the Solcast API! Error message: {err}')


def store_solcast(df):
    try:
        engine = get_engine()
        # delete existing values
        delete_query = f"""DELETE FROM solar_forecast WHERE timestamp IN {tuple(df.index.strftime(TIME_FORMAT))}"""
        with engine.connect() as conn:
            conn.execute(delete_query)
        df.to_sql('solar_forecast', engine, if_exists='append',
                  index=True, index_label='timestamp')
    except Exception as err:
        logger.error(
            f'** Solcast: Error writing solar forecast data to DB! Error message: {err}')


# get the data and store it
solar_forecast = get_solcast_data(API_BASE_URL, solcast_api_key, solcast_site)
store_solcast(solar_forecast)

logger.info('*** PyElectricity: Solcast terminating ***')
