import numpy as np
import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
from nordpool import elspot
from config import get_engine, setup_logger, TIME_FORMAT
from sqlalchemy import text


logger = setup_logger('Power', level='INFO')
logger.info('*** PyElectricity: Power starting ***')


today = dt.now().date()
tomorrow = dt.now().date() + timedelta(days=+1)

areas = ['DK2']
currency = 'DKK'
prices = elspot.Prices(currency=currency)

prices_today = prices.hourly(areas=areas, end_date=today)[
    'areas']['DK2']['values']
prices_tomorrow = prices.hourly(areas=areas, end_date=tomorrow)[
    'areas']['DK2']['values']

df = pd.DataFrame(data=prices.hourly(areas=areas)['areas']['DK2']['values'])
df = pd.concat([pd.DataFrame(data=prices_today), pd.DataFrame(
    data=prices_tomorrow)]).reset_index(drop=True).set_index('start').drop(columns=['end']).rename(columns={'value': 'price'})

df['price'] = df['price'] / 1000

df['rolling_sum'] = df['price'].rolling(3).sum().shift(-2)

# lowest_value = df['rolling_sum'].min()
# lowest_three = sorted(df['rolling_sum'].values)[:3]

df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['price'])
df['currency'] = currency

# in case of daily saving time changes we may get a duplicated key:
if any(df.index.duplicated(keep='last')):
    df['time'] = df.index
    df.loc[df.index.duplicated(keep='last'), 'time'] = df[df.index.duplicated(
        keep='last')].time - np.timedelta64(1, 'h')
    df = df.set_index('time', drop=True)

try:
    engine = get_engine()
    # delete what we have in the dataframe -- plus anything older than 7 days?
    # delete_query = f"""DELETE FROM price_data WHERE timestamp IN {tuple(df.index.strftime(TIME_FORMAT))} OR timestamp < '{(dt.now()).strftime(TIME_FORMAT)}'"""
    delete_query = f"""DELETE FROM price_data WHERE timestamp IN {tuple(df.index.strftime(TIME_FORMAT))}"""
    with engine.connect() as conn:
        # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
        conn.execute(text(delete_query))

    # and insert the dataframe keeping on the future prices -- removed to do time analysis
    #df = df[df.index > (dt.now() - timedelta(hours=1)).strftime(TIME_FORMAT)]
    df.to_sql('price_data', engine, if_exists='append',
              index=True, index_label='timestamp')
    logger.debug(f'Power: Write some data to the DB, {df.shape[0]} rows')
except Exception as err:
    logger.error(
        f'Power: Error writing to DB! Error message: {err}')

logger.info('*** PyElectricity: Power terminating ***')
