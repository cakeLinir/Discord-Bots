import sqlite3


def initialize_database():
    connection = sqlite3.connect("clash_bot.db")
    cursor = connection.cursor()

    # Tabelle für Event-Kanäle
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL UNIQUE,
        channel_id INTEGER NOT NULL
    )
    """)

    # Tabelle für Spieler
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_tag TEXT UNIQUE NOT NULL,
            discord_id INTEGER UNIQUE NOT NULL,
            coc_name TEXT NOT NULL,
            clan_name TEXT NOT NULL,
            townhall_level INTEGER NOT NULL,
            role TEXT NOT NULL,
            last_verified TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    # Tabelle für Clan-Kriege
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clan_wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        war_id TEXT UNIQUE,
        start_time TEXT,
        end_time TEXT,
        state TEXT,
        clan_name TEXT,
        opponent_name TEXT,
        clan_stars INTEGER,
        opponent_stars INTEGER,
        clan_percentage REAL,
        opponent_percentage REAL
    )
    """)

    # Tabelle für CWL (Clan War League)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cwl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id TEXT UNIQUE,
        start_time TEXT,
        end_time TEXT,
        clan_name TEXT,
        opponent_name TEXT,
        clan_stars INTEGER,
        opponent_stars INTEGER
    )
    """)

    # Tabelle für Clanspiele
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clanspiele (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        end_time TEXT,
        progress INTEGER DEFAULT 0,
        total_points INTEGER DEFAULT 50000,
        message_id INTEGER,
        channel_id INTEGER
    )
    """)

    # Tabelle für Spielerpunkte in Clanspielen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clanspiele_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clanspiele_id INTEGER NOT NULL,
        player_tag TEXT NOT NULL,
        coc_name TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        discord_id INTEGER,
        FOREIGN KEY (clanspiele_id) REFERENCES clanspiele (id) ON DELETE CASCADE,
        FOREIGN KEY (player_tag) REFERENCES players (player_tag) ON DELETE CASCADE
    )
    """)

    # Tabelle für Clan-Stadt
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clan_city (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_name TEXT NOT NULL,
        current_level INTEGER DEFAULT 0,
        total_contributions INTEGER DEFAULT 0,
        last_updated TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabelle für Clan-Stadt-Beiträge der Spieler
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clan_city_contributors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_city_id INTEGER NOT NULL,
        player_tag TEXT NOT NULL,
        coc_name TEXT NOT NULL,
        contributions INTEGER DEFAULT 0,
        last_contribution_time TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (clan_city_id) REFERENCES clan_city (id) ON DELETE CASCADE,
        FOREIGN KEY (player_tag) REFERENCES players (player_tag) ON DELETE CASCADE
    )
    """)

    connection.commit()
    connection.close()
    print("Datenbank erfolgreich initialisiert.")

