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
