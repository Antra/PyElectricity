import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
import numpy as np
import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
from nordpool import elspot
import os

load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db = os.getenv("DB")

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

# delete overlap and store new
time_format = '%Y-%m-%d %H:%M:%S%z'
# connect_string = f'host={db_host} port={db_port} user={db_user} password={db_pass} dbname={db}'

engine = create_engine(
    f'postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db}')

# engine.connect()

# delete what we have in the dataframe plus anything older than 7 days
#delete_query = f"""DELETE FROM price_data WHERE timestamp IN {tuple(df.index.strftime(time_format))} OR timestamp < '{(df.index.min() - timedelta(days=7)).strftime(time_format)}'"""
delete_query = f"""DELETE FROM price_data WHERE timestamp IN {tuple(df.index.strftime(time_format))} OR timestamp < '{(dt.now()).strftime(time_format)}'"""

with engine.connect() as conn:
    conn.execute(delete_query)

# and insert the dataframe keeping on the future prices
df = df[df.index > (dt.now() - timedelta(hours=1)).strftime(time_format)]
df.to_sql('price_data', engine, if_exists='append',
          index=True, index_label='timestamp')
