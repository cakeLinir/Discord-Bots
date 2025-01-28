
-- Erstellen der Datenbank
CREATE DATABASE IF NOT EXISTS clashofclans_bot;
USE clashofclans_bot;

-- Tabelle für Benutzer
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT UNIQUE,
    player_tag VARCHAR(20) NOT NULL UNIQUE,
    coc_name VARCHAR(50) NOT NULL,
    role VARCHAR(20),
    warn_time INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabelle für Event-Kanäle
CREATE TABLE IF NOT EXISTS event_channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL
);

-- Tabelle für Clan-Spiele
CREATE TABLE IF NOT EXISTS clanspiele (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    progress INT DEFAULT 0,
    message_id BIGINT,
    channel_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabelle für Spieler in Clan-Spielen
CREATE TABLE IF NOT EXISTS clanspiele_players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clanspiele_id INT NOT NULL,
    player_tag VARCHAR(20) NOT NULL,
    coc_name VARCHAR(50) NOT NULL,
    points INT DEFAULT 0,
    discord_id BIGINT,
    FOREIGN KEY (clanspiele_id) REFERENCES clanspiele(id) ON DELETE CASCADE
);

-- Tabelle für Clan-Kriege
CREATE TABLE IF NOT EXISTS clan_wars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    clan_name VARCHAR(50) NOT NULL,
    opponent_name VARCHAR(50) NOT NULL,
    clan_stars INT DEFAULT 0,
    opponent_stars INT DEFAULT 0,
    message_id BIGINT,
    channel_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabelle für Spieler in Clan-Kriegen
CREATE TABLE IF NOT EXISTS clan_war_players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    war_id INT NOT NULL,
    player_tag VARCHAR(20) NOT NULL,
    coc_name VARCHAR(50) NOT NULL,
    stars INT DEFAULT 0,
    townhall_level INT NOT NULL,
    is_opponent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (war_id) REFERENCES clan_wars(id) ON DELETE CASCADE
);

-- Beispielinhalte für die event_channels-Tabelle
INSERT INTO event_channels (event_type, channel_id) VALUES
('clanspiele', 1326612623642595399), -- Ersetze durch die echte Channel-ID
('clan_war', 1326612533939011686), -- Ersetze durch die echte Channel-ID
('clan_war_league', 1326612361196474440); -- Ersetze durch die echte Channel-ID

