import aiomysql
from tinydb import TinyDB, Query
import os

# Datenbankpfad
DB_PATH = os.path.join(os.getcwd(), 'db.json')

# Datenbank initialisieren
db = TinyDB(DB_PATH)

def get_table(name):
    """Gibt eine bestimmte Tabelle zurück."""
    return db.table(name)

def upsert_into_table(table_name, data, query):
    """
    Fügt Daten ein oder aktualisiert sie, falls ein Eintrag vorhanden ist.
    :param table_name: Name der Tabelle
    :param data: Daten, die eingefügt oder aktualisiert werden sollen
    :param query: Bedingung für das Upsert
    """
    table = get_table(table_name)
    table.upsert(data, query)

def get_all_from_table(table_name):
    """Holt alle Daten aus einer Tabelle."""
    table = get_table(table_name)
    return table.all()

def remove_from_table(table_name, query):
    """Entfernt Einträge basierend auf einer Abfrage."""
    table = get_table(table_name)
    table.remove(query)

async def get_db_connection():
    """Erstelle eine Verbindung zur MySQL-Datenbank."""
    return await aiomysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
    )

async def execute_query(query, params=None, fetch=False):
    """Führt eine Abfrage aus und gibt optional Ergebnisse zurück."""
    conn = await get_db_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params or ())
            if fetch:
                return await cursor.fetchall()
            await conn.commit()
    finally:
        conn.close()
