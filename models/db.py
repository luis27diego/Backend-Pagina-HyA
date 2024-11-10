import psycopg2
from config import Config

def get_db_connection():
    config = Config()
    if not config.DATABASE_URL:
        raise Exception("DATABASE_URL no está configurada")
    try:
        conn = psycopg2.connect(config.DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {str(e)}")
        raise
