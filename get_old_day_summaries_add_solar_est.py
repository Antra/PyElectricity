import numpy as np
import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
from config import setup_logger, get_engine
from sqlalchemy import text

# logger = setup_logger('Computation', level='INFO')
# logger.info('*** PyElectricity: Computation starting ***')

yesterday = dt.utcnow() - timedelta(hours=24)
now = dt.utcnow()

# get the newest date we have data for
engine = get_engine()
query = f"""SELECT min(date) FROM daily_summary where daily_solar_est is null"""
with engine.connect() as conn:
    # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
    oldest_date = conn.execute(text(query)).fetchone()[0]

cut_off_date = oldest_date + timedelta(days=90)

query = f"""select
                date, min_battery, max_battery, min_battery_raw, max_battery_raw, first_1kw, last_1kw, first_2kw, last_2kw, first_prod, last_prod, peak_solar, daily_total, daily_solar_est
            from daily_summary
            where date >= '{oldest_date}'
            and date < '{cut_off_date}'
        """

summary = pd.read_sql(query, engine)

query = f"""select
                timestamp, p_solar
            from inverter_data inv
            where inv.timestamp >= '{oldest_date}'
            and inv.timestamp < '{cut_off_date}'
        """


details = pd.read_sql(query, engine, parse_dates=['timestamp']).set_index(
    'timestamp').resample('S').bfill()
# summary['diary_date'] = summary['diary_date'].astype(str)

if details.shape[0] > 0:
    est_dict = {str(k): v for k, v in details.groupby(details.index.date)[
        'p_solar'].agg(lambda x: x.sum()/3600000).to_dict().items()}
    summary['daily_solar_est'] = pd.to_datetime(
        summary['date']).dt.strftime('%Y-%m-%d').map(est_dict).fillna(0)
    del est_dict
else:
    summary['daily_solar_est'] = summary['daily_solar_est'].fillna(0)

summary.sort_values(by='date', ascending=True, ignore_index=True, inplace=True)


# delete the old date and replace it
engine = get_engine()
delete_query = f"""DELETE FROM daily_summary WHERE date IN {tuple(pd.to_datetime(summary['date']).dt.strftime('%Y-%m-%d'))}"""
with engine.connect() as conn:
    # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
    conn.execute(text(delete_query))
    conn.commit()
    del delete_query

summary.to_sql('daily_summary', engine, if_exists='append', index=False)


del details
del summary
