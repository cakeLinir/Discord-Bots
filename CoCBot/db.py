import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def initialize_database():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("COC_DB_NAME")
    )
    with connection.cursor() as cursor:
        # Users-Tabelle
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id BIGINT PRIMARY KEY,
            player_tag VARCHAR(15) NOT NULL UNIQUE,
            encrypted_token TEXT NOT NULL,
            role VARCHAR(20) NOT NULL
        );
        """)

        # Event-Channels-Tabelle
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_channels (
            event_name VARCHAR(50) PRIMARY KEY,
            channel_id BIGINT NOT NULL
        );
        """)
    connection.commit()
    connection.close()

# Datenbank initialisieren
initialize_database()
