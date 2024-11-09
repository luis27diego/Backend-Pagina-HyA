import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde .env

class Config:
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    secret_key = os.getenv('SECRET_KEY')
