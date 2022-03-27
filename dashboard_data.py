import pandas as pd
from config import get_engine, setup_logger
from datetime import timedelta

logger = setup_logger('Dashboard Data', level='INFO')


def get_battery_state():
    try:
        engine = get_engine()
        query = f"""
            SELECT
                timestamp,
                battery_state_norm
            FROM inverter_data
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        # with engine.connect() as conn:
        #     battery_pct = conn.execute(query).fetchone()[0]
        #     logger.debug(
        #         '** Dashboard Data: fetched battery normalised state: %s %%', str(battery_pct))
        #     return battery_pct

        df = pd.read_sql(query, engine, parse_dates=['timestamp'])
        return df

    except Exception as err:
        logger.error(
            f'** Dashboard Data: Error getting battery state from DB! Error message: {err}')


def get_solar_prediction(base_date):
    try:
        engine = get_engine()
        query = f"""
            SELECT
                timestamp,
                pv_estimate,
                pv_estimate10,
                pv_estimate90
            FROM solar_forecast
            WHERE timestamp >= '{base_date}'
            AND timestamp < '{base_date + timedelta(days=+3)}'
            ORDER BY timestamp ASC
            LIMIT 250
        """
        df = pd.read_sql(query, engine, parse_dates=['timestamp'])
        return df

    except Exception as err:
        logger.error(
            f'** Dashboard Data: Error getting solar predictions from DB! Error message: {err}')


def get_sunrise(base_date):
    try:
        engine = get_engine()
        query = f"""
            SELECT
                sunrise,
                sunset
            FROM weather_sunrise
            WHERE date = '{base_date}'
            LIMIT 1
        """
        with engine.connect() as conn:
            sunrise = conn.execute(query).fetchone()
            return sunrise

    except Exception as err:
        logger.error(
            f'** Dashboard Data: Error getting sunrise/sunset data from DB! Error message: {err}')
