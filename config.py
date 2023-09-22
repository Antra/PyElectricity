from dotenv import load_dotenv
import os
from logging.handlers import RotatingFileHandler
import logging
from sqlalchemy import create_engine
import psycopg2


load_dotenv()

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db = os.getenv("DB")
inverter_ip = os.getenv("INVERTERIP")
freq = int(os.getenv("QUERY_FREQUENCY"))
threshold = int(os.getenv("THRESHOLD"))
weather_api_key = os.getenv("WEATHER_API")
latitude = os.getenv("WEATHER_LAT")
longitude = os.getenv("WEATHER_LON")
solcast_api_key = os.getenv("SOLCAST_API")
solcast_site = os.getenv("SOLCAST_SITE")


tuya_device_config = {'device1_id': os.getenv('DEVICE1_ID', None),
                      'device1_key': os.getenv('DEVICE1_KEY', None),
                      'device2_id': os.getenv('DEVICE2_ID', None),
                      'device2_key': os.getenv('DEVICE2_KEY', None),
                      'device3_id': os.getenv('DEVICE3_ID', None),
                      'device3_key': os.getenv('DEVICE3_KEY', None),
                      'device4_id': os.getenv('DEVICE4_ID', None),
                      'device4_key': os.getenv('DEVICE4_KEY', None),
                      'device5_id': os.getenv('DEVICE5_ID', None),
                      'device5_key': os.getenv('DEVICE5_KEY', None),
                      'device6_id': os.getenv('DEVICE6_ID', None),
                      'device6_key': os.getenv('DEVICE6_KEY', None),
                      'device7_id': os.getenv('DEVICE7_ID', None),
                      'device7_key': os.getenv('DEVICE7_KEY', None),
                      'device8_id': os.getenv('DEVICE8_ID', None),
                      'device8_key': os.getenv('DEVICE8_KEY', None),
                      'device9_id': os.getenv('DEVICE9_ID', None),
                      'device9_key': os.getenv('DEVICE9_KEY', None)
                      }
# remove the devices we don't actually have to speed up
tuya_device_config = {k: v for k, v in tuya_device_config.items() if v}
tuya_device_count = len(tuya_device_config) // 2


TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

loggers = {}
connect_string = f'host={db_host} port={db_port} user={db_user} password={db_pass} dbname={db}'


def setup_logger(logger_name, log_file='pyelectricity.log', level=logging.INFO):
    # Get the basic logging set up
    logger = logging.getLogger(logger_name)
    log_folder = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_folder, log_file)
    logger.setLevel(level)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=102400, backupCount=2)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s', TIME_FORMAT)
    file_handler.setFormatter(formatter)
    if not logger_name in loggers.keys():
        logger.addHandler(file_handler)
        loggers[logger_name] = True
    return logger


def get_engine():
    return create_engine(f'postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db}')


def get_connection():
    return psycopg2.connect(connect_string)
