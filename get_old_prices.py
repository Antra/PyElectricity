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

# get last two years
max_days = (dt.now() - dt(dt.now().year-3, 12, 31)).days

data = []

for num in range(0, max_days, 1):
    older_days = dt.now().date() + timedelta(days=-num)

    df = pd.DataFrame(data=prices.hourly(
        areas=areas, end_date=older_days)['areas']['DK2']['values'])
    data.append(df)


df = pd.concat(data).sort_values(by='start').drop(
    columns=['end']).rename(columns={'value': 'price'})
df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['price']).drop_duplicates(
    subset=['start'], keep='last').reset_index(drop=True).set_index('start')


df['price'] = df['price'] / 1000


df['rolling_sum'] = df['price'].rolling(3).sum().shift(-2)
df['currency'] = currency
df[df['rolling_sum'].isna()]


engine = get_engine()
delete_query = f"""DELETE FROM price_data WHERE timestamp IN {tuple(df.index.strftime(TIME_FORMAT))}"""
with engine.connect() as conn:
    # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
    conn.execute(text(delete_query))
    conn.commit()

df.to_sql('price_data', engine, if_exists='append',
          index=True, index_label='timestamp')
