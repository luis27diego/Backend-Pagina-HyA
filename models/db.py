import psycopg2
from config import Config

def get_db_connection():
    conn = psycopg2.connect(
        host=Config.POSTGRES_HOST,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        dbname=Config.POSTGRES_DB
    )
    return conn
