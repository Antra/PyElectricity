import os
from datetime import datetime as dt
from time import sleep
import logging
from logging.handlers import RotatingFileHandler

import requests
import psycopg2
from dotenv import load_dotenv

# Get the basic logging set up
logger = logging.getLogger(__name__)
log_folder = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_folder, 'pyelectricity.log')
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(log_file, maxBytes=102400, backupCount=2)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('*** PyElectricity starting ***')

load_dotenv()

inverter_ip = os.getenv("INVERTERIP")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db = os.getenv("DB")
freq = int(os.getenv("QUERY_FREQUENCY"))
threshold = int(os.getenv("THRESHOLD"))


def _get_data():
    url = f'http://{inverter_ip}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
    data = {}
    try:
        response = requests.get(url).json()
        if response:
            # effect to/from battery(positive is discharge, negative is charge)
            data['p_akku'] = response['Body']['Data']['Site']['P_Akku'] or 0
            # effect to/from grid(positive is from grid, negative is to grid)
            data['p_grid'] = response['Body']['Data']['Site']['P_Grid'] or 0
            # effect used in local net(negative is consuming, positive is generating)
            data['p_load'] = response['Body']['Data']['Site']['P_Load'] or 0
            # effect from solar panels(positive is production)
            data['p_pv'] = response['Body']['Data']['Site']['P_PV'] or 0
            # self-consumption(how much PV power is being at home (not exported))
            data['rel_self'] = response['Body']['Data']['Site']['rel_SelfConsumption'] or 0
            # self-sufficiency(how much power is self-supplied (not imported))
            data['rel_auto'] = response['Body']['Data']['Site']['rel_Autonomy'] or 0
            # current effect in watt (positive is produced/exporting, negative is consuing/importing) - abs sum of P_Load+P_Grid?
            data['p'] = response['Body']['Data']['Inverters']['1']['P'] or 0
            # battery level; NB, recommendation is to keep the battery within 12%-98% SoC
            data['soc'] = response['Body']['Data']['Inverters']['1']['SOC'] or 0
            # battery level, normalised percentage: (SOC-12)*100/86 %
            data['soc_normal'] = round((data['soc']-12)*100/86, 1) or 0
            # tz-aware timestamp of recording
            date_format = '%Y-%m-%dT%H:%M:%S%z'
            data['timestamp'] = dt.strptime(
                response['Head']['Timestamp'], date_format)
            logger.debug(f'Fetched some data from the inverter: {data}')
            return data
    except Exception as err:
        logger.error(
            f'Error getting data from the inverter! Error message: {err}')
        empty_reponse = {
            'timestamp': None,
            'p_akku': None,
            'p_grid': None,
            'p_load': None,
            'p_pv': None,
            'rel_self': None,
            'rel_auto': None,
            'p': None,
            'soc': None,
            'soc_normal': None
        }
        return empty_reponse


def _store_data(data):
    query = f"""
        INSERT INTO inverter_data (
            timestamp,
            p_battery,
            p_grid,
            p_local,
            p_solar,
            pct_selfsufficient,
            pct_autonomy,
            p_total,
            battery_state,
            battery_state_norm)
        VALUES (
            '{data['timestamp']}',
            {data['p_akku']},
            {data['p_grid']},
            {data['p_load']},
            {data['p_pv']},
            {data['rel_self']},
            {data['rel_auto']},
            {data['p']},
            {data['soc']},
            {data['soc_normal']}
        );
    """
    connect_string = f'host={db_host} port={db_port} user={db_user} password={db_pass} dbname={db}'
    try:
        if data['timestamp']:
            with psycopg2.connect(connect_string) as conn:
                cur = conn.cursor()
                cur.execute(query)
                cur.close()
                conn.commit()
        else:
            logger.error(
                f'** Error saving the following to the database: {data} **')
    except Exception as err:
        logger.error(
            f'** Error saving to database! Error message: {err} ** trying to save {query} **')


if __name__ == '__main__':
    counter = 0
    # My Raspberry Pi dislikes the script for hours and hours, so re-running it every X mins instead
    while counter <= threshold:
        try:
            data = _get_data()
            _store_data(data)
            sleep(freq)
        except Exception as err:
            logger.error(f'** Outer loop failed: {err} **')
        counter += 1
    logger.info('*** PyElectricity terminating ***')
