import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde .env

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL')  # Añade esta línea
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    secret_key = os.getenv('SECRET_KEY')
    
    def __init__(self):
        print(f"POSTGRES_HOST: {self.POSTGRES_HOST}")
        print(f"POSTGRES_USER: {self.POSTGRES_USER}")
        print(f"POSTGRES_DB: {self.POSTGRES_DB}")