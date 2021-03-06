import os
from datetime import datetime as dt

import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

inverter_ip = os.getenv("INVERTERIP")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")


url = f'http://{inverter_ip}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'

data = requests.get(url).json()

p_akku = data['Body']['Data']['Site']['P_Akku']
p_grid = data['Body']['Data']['Site']['P_Grid']
p_load = data['Body']['Data']['Site']['P_Load']
p_pv = data['Body']['Data']['Site']['P_PV']
rel_self = data['Body']['Data']['Site']['rel_SelfConsumption']
rel_auto = data['Body']['Data']['Site']['rel_Autonomy']
p = data['Body']['Data']['Inverters']['1']['P']
soc = data['Body']['Data']['Inverters']['1']['SOC']
#timestamp = data['Head']['Timestamp']
date_format = '%Y-%m-%dT%H:%M:%S%z'
timestamp = dt.strptime(data['Head']['Timestamp'], date_format)


print(p_akku)  # effect to/from battery(positive is discharge, negative is charge)
print(p_grid)  # effect to/from grid(positive is from grid, negative is to grid)
print(p_load)  # effect used in local net(negative is consuming, positive is generating)
print(p_pv)  # effect from solar panels(positive is production)
print(rel_self)  # percentage of self-consumption
print(rel_auto)  # ??
print(p)  # current effect in watt (positive is produced/exporting, negative is consuing/importing) - abs sum of P_Load+P_Grid?
print(soc)  # battery level
print(timestamp)  # tz-aware timestamp of recording
