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
query = f"""SELECT min(date) FROM daily_summary where night_grid_charge is null"""
with engine.connect() as conn:
    # wrap query in text() when executing, https://stackoverflow.com/questions/69490450/objectnotexecutableerror-when-executing-any-sql-query-using-asyncengine
    oldest_date = conn.execute(text(query)).fetchone()[0]

cut_off_date = oldest_date + timedelta(days=90)


query = f"""
            with battery_snapshot as (
				SELECT * FROM (
					SELECT
						timestamp::date as diary_date,
						ROW_NUMBER() OVER (PARTITION BY timestamp::date ORDER BY abs(extract(epoch from (timestamp::time - '01:00:00'::time))) ASC) as row_num_1am,
						ROW_NUMBER() OVER (PARTITION BY timestamp::date ORDER BY abs(extract(epoch from (timestamp::time - '05:00:00'::time))) ASC) as row_num_5am,
						battery_state
					from public.inverter_data inv
					where timestamp::time < '08:00:00'::time
                    and inv.timestamp >= '{oldest_date}'
                    and inv.timestamp < '{cut_off_date}'
					)
					where (row_num_1am = 1 OR row_num_5am = 1)
			)
            select
                date, min_battery, max_battery, min_battery_raw, max_battery_raw, first_1kw, last_1kw, first_2kw, last_2kw, first_prod, last_prod, peak_solar, daily_total, daily_solar_est,
                COALESCE(snap1am.battery_state, 0) as battery_at_1am,
				COALESCE(snap5am.battery_state, 0) as battery_at_5am,
				CASE
					WHEN COALESCE(snap1am.battery_state, 0)+10 < COALESCE(snap5am.battery_state, 0) THEN TRUE
					ELSE FALSE
				END as night_grid_charge
            from daily_summary summary
            left join battery_snapshot snap1am on summary.date = snap1am.diary_date and snap1am.row_num_1am = 1
            left join battery_snapshot snap5am on summary.date = snap5am.diary_date and snap5am.row_num_5am = 1
            where date >= '{oldest_date}'
            and date < '{cut_off_date}'
        """


summary = pd.read_sql(query, engine)


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

del summary
