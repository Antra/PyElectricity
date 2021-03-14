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


def _get_data():
    url = f'http://{inverter_ip}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
    data = {}
    try:
        response = requests.get(url).json()
        # effect to/from battery(positive is discharge, negative is charge)
        data['p_akku'] = response['Body']['Data']['Site']['P_Akku']
        # effect to/from grid(positive is from grid, negative is to grid)
        data['p_grid'] = response['Body']['Data']['Site']['P_Grid']
        # effect used in local net(negative is consuming, positive is generating)
        data['p_load'] = response['Body']['Data']['Site']['P_Load']
        # effect from solar panels(positive is production)
        data['p_pv'] = response['Body']['Data']['Site']['P_PV']
        # self-consumption(how much PV power is being at home (not exported))
        data['rel_self'] = response['Body']['Data']['Site']['rel_SelfConsumption']
        # self-sufficiency(how much power is self-supplied (not imported))
        data['rel_auto'] = response['Body']['Data']['Site']['rel_Autonomy']
        # current effect in watt (positive is produced/exporting, negative is consuing/importing) - abs sum of P_Load+P_Grid?
        data['p'] = response['Body']['Data']['Inverters']['1']['P']
        # battery level; NB, recommendation is to keep the battery within 12%-98% SoC
        data['soc'] = response['Body']['Data']['Inverters']['1']['SOC']
        # battery level, normalised percentage: (SOC-12)*100/86 %
        data['soc_normal'] = round((data['soc']-12)*100/86, 1)
        # tz-aware timestamp of recording
        date_format = '%Y-%m-%dT%H:%M:%S%z'
        data['timestamp'] = dt.strptime(
            response['Head']['Timestamp'], date_format)
        logger.debug(f'Fetched some data from the inverter: {data}')
        return data
    except Exception as err:
        logger.error(
            f'Error getting data from the inverter! Error message: {err.message}')


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
        with psycopg2.connect(connect_string) as conn:
            cur = conn.cursor()
            cur.execute(query)
            cur.close()
            conn.commit()
    except Exception as err:
        logger.error(
            f'Error saving to database! Error message: {err.message}')


if __name__ == '__main__':
    while True:
        data = _get_data()
        _store_data(data)
        sleep(freq)
