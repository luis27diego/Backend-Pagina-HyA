import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL')
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    def __init__(self):
        print(f"DATABASE_URL: {self.DATABASE_URL}")  # Para debug