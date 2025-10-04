import pandas as pd
from config import get_engine, setup_logger
from datetime import timedelta
from sqlalchemy import text
import pytz

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
        df['battery_state_norm'] = df['battery_state_norm'].clip(0, 100)
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
                sunset,
                summary
            FROM weather_sunrise
            WHERE date = '{base_date}'
            LIMIT 1
        """
        with engine.connect() as conn:
            # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
            sunrise = conn.execute(text(query)).fetchone()
            return sunrise
    except Exception as err:
        logger.error(
            f'** Dashboard Data: Error getting sunrise/sunset data from DB! Error message: {err}')


def _get_offset(datetime, tz_info=None):
    """add the price offset for delivery of electricity (incl tax)
    For Radius see: https://radiuselnet.dk/elnetkunder/tariffer-og-netabonnement
    """
    month, time = datetime.month, datetime.hour

    tariffs = {
        'summer': {'low': 0.1220, 'high': 0.1831, 'peak': 0.4760},
        'winter': {'low': 0.1220, 'high': 0.3661, 'peak': 1.0985}
    }

    period = 'summer' if month in [4, 5, 6, 7, 8, 9] else 'winter'

    rate = 'low' if time in [0, 1, 2, 3, 4, 5] else None
    rate = 'peak' if not rate and time in [17, 18, 19, 20] else rate
    rate = 'high' if not rate and time in [
        6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23] else rate

    offset = tariffs.get(period, {}).get(rate, 0)

    return offset


def get_prices(base_date, tz=None, limit=100):
    try:
        engine = get_engine()
        query = f"""
            SELECT
                timestamp,
                price,
                rolling_sum,
                currency
            FROM price_data
            WHERE timestamp >= '{base_date}'
            ORDER BY timestamp ASC
            LIMIT {limit}
        """
        df = pd.read_sql(query, engine, parse_dates=['timestamp'])
        if tz:
            df['offset'] = df.apply(lambda x: _get_offset(
                x['timestamp'].astimezone(tz=pytz.timezone(timezone))), axis=1)
        else:
            df['offset'] = df.apply(
                lambda x: _get_offset(x['timestamp']), axis=1)
        return df

    except Exception as err:
        logger.error(
            f'** Dashboard Data: Error getting electricity prices from DB! Error message: {err}')
