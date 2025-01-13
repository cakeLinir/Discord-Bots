import asyncio
import json
import os
import warnings
from datetime import datetime, timezone, timedelta
import sys
import discord
import requests
from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv
from tinydb import TinyDB, Query

warnings.filterwarnings("ignore", category=DeprecationWarning)

threshold_date = datetime.now(timezone.utc) - timedelta(days=30)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Lade die Umgebungsvariablen
load_dotenv("../.env")

def get_bot_token(bot_name):
    """Gibt den Bot-Token basierend auf dem Namen zurück."""
    token_key = f"DISCORD_TOKEN_{bot_name.upper()}"
    token = os.getenv(token_key)
    if not token:
        raise ValueError(f"Kein Token für den Bot '{bot_name}' gefunden. Überprüfe die .env-Datei.")
    return token

# Prüfe, ob ein Bot-Name als Argument übergeben wurde
if len(sys.argv) > 1:
    BOT_NAME = sys.argv[1].lower()  # Argument für den Bot-Namen
else:
    BOT_NAME = "clash"  # Standardwert, wenn kein Argument angegeben wurde

if BOT_NAME != "clash":
    raise ValueError(f"Ungültiger Bot-Name '{BOT_NAME}'. Erwartet wurde: 'clash'")

print(f"Starte Bot: {BOT_NAME}")

# Hole den spezifischen Bot-Token
DISCORD_TOKEN = get_bot_token(BOT_NAME)

# Zusätzliche Umgebungsvariablen
COC_API_TOKEN = os.getenv("COC_API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")

if not DISCORD_TOKEN or not COC_API_TOKEN or not CLAN_TAG:
    raise ValueError("Eine oder mehrere Umgebungsvariablen fehlen. Bitte überprüfe die .env-Datei.")

print(f"CLAN_TAG loaded: {CLAN_TAG}")

# Load role and channel mapping from config.json
def load_config():
    if not os.path.exists("config.json"):
        with open("config.json", "w") as config_file:
            default_config = {
                "roles": {"Leader": "", "Co-Leader": "", "Elder": "", "Member": ""},
                "channels": {"CK": "", "CWL": "", "Clangames": ""}
            }
            json.dump(default_config, config_file, indent=4)
        print("Default config.json created.")
    with open("config.json", "r") as config_file:
        return json.load(config_file)

def save_config(config):
    with open("config.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

CONFIG = load_config()
ROLE_MAPPING = CONFIG.get("roles", {})
CHANNEL_MAPPING = CONFIG.get("channels", {})

# Initialize the bot
intents = discord.Intents.default()
intents.all()
client = commands.Bot(command_prefix="/", intents=intents)
tree = client.tree

# Database setup using TinyDB
db = TinyDB('db.json')
verified_users = db.table('verified_users')

# Clash of Clans API request
headers = {
    "Authorization": f"Bearer {COC_API_TOKEN}"
}

def initialize_db():
    """Initialisiert die Datenbank mit Standardwerten, falls nicht vorhanden."""
    db_file = "db.json"
    try:
        with open(db_file, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}  # Initialisiere leere Datenbank

    if "messages" not in data:
        data["messages"] = {}

    with open(db_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Rufe die Initialisierungsfunktion beim Start des Bots auf
initialize_db()

def save_message_id(channel_name, message_id):
    """Speichert die Nachricht-ID in der Datenbank."""
    db_file = "db.json"
    try:
        # Lade die Datenbank
        with open(db_file, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        # Erstelle die Datei, wenn sie nicht existiert
        data = {}
    except json.JSONDecodeError:
        # Initialisiere, wenn die Datei leer oder beschädigt ist
        data = {}

    # Stelle sicher, dass der Schlüssel "messages" existiert
    if "messages" not in data:
        data["messages"] = {}

    # Speichere die Nachricht-ID
    data["messages"][channel_name] = message_id

    # Schreibe die Daten zurück
    with open(db_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def get_message_id(channel_name):
    """Holt die Nachricht-ID aus der Datenbank."""
    db_file = "db.json"
    try:
        with open(db_file, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None  # Keine Datenbank oder fehlerhafte Struktur

    # Gib die Nachricht-ID zurück, falls vorhanden
    return data.get("messages", {}).get(channel_name)

def fetch_player_data(player_tag):
    url = f"https://api.clashofclans.com/v1/players/%23{player_tag.strip('#')}"
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None



def fetch_clan_war():
    """Ruft die Daten des aktuellen Clan-Kriegs von der Clash of Clans API ab."""
    url = f"https://api.clashofclans.com/v1/clans/%23{CLAN_TAG}/currentwar"
    headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            # Überprüfe, ob ein Krieg aktiv ist
            if data.get("state") in ["inWar", "preparation"]:
                return data
            else:
                return None  # Kein laufender oder vorbereitender Krieg
        elif response.status_code == 404:
            return None  # Kein Krieg gefunden
        else:
            raise Exception(f"API-Fehler: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Fehler beim Abrufen des Clan-Kriegs: {e}")
        return None

def fetch_cwl():
    """Ruft die Daten der aktuellen CWL (Clan-War-League) ab."""
    url = f"https://api.clashofclans.com/v1/clans/%23{CLAN_TAG}/currentwar"
    headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            # Prüfe, ob CWL-Daten verfügbar sind
            if data.get("state") == "inWar" and data.get("warLeague"):
                return data
            elif data.get("state") == "notInWar":
                print("Kein aktiver CWL-Krieg gefunden.")
                return None
            else:
                print("Unerwarteter Zustand der CWL-Daten:", data.get("state"))
                return None
        elif response.status_code == 404:
            print("CWL-Daten nicht verfügbar (404).")
            return None
        else:
            print(f"API-Fehler: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Fehler beim Abrufen der CWL-Daten: {e}")
        return None

def fetch_clan_games():
    """Lädt die Clan-Games-Daten aus der JSON-Datei."""
    try:
        with open("db.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("clangames")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def is_player_in_clan(player_data):
    return player_data.get("clan", {}).get("tag") == CLAN_TAG

CLAN_ROLE_MAPPING = {
    "leader": "Leader",
    "coleader": "Co-Leader",
    "elder": "Elder",
    "member": "Member"
}

def get_discord_role(guild, clan_role):
    clan_role_mapping = {
        "leader": "Leader",
        "coleader": "Co-Leader",
        "elder": "Elder",
        "member": "Member"
    }
    role_name = clan_role_mapping.get(clan_role)
    if not role_name:
        return None

    role_id = ROLE_MAPPING.get(role_name)
    return guild.get_role(int(role_id)) if role_id else None

def is_cwl_active():
    """Prüft, ob CWL-Kriege aktiv sind."""
    url = f"https://api.clashofclans.com/v1/clans/%23{CLAN_TAG}/currentwar"
    headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return False  # Kein aktiver CWL-Krieg
    elif response.status_code == 200:
        return True  # CWL-Krieg aktiv
    else:
        print(f"Unerwarteter API-Status: {response.status_code}")
        return False

async def ensure_roles(guild):
    updated_mapping = ROLE_MAPPING.copy()
    for clan_role in ["Leader", "Co-Leader", "Elder", "Member"]:
        role_id = updated_mapping.get(clan_role, "")
        discord_role = guild.get_role(int(role_id)) if role_id.isdigit() else None
        if not discord_role:
            discord_role = await guild.create_role(name=clan_role)
            updated_mapping[clan_role] = str(discord_role.id)
    CONFIG["roles"] = updated_mapping
    save_config(CONFIG)

async def ensure_event_channels(guild):
    updated_channels = CHANNEL_MAPPING.copy()
    for event in ["CK", "CWL", "Clangames"]:
        channel_id = updated_channels.get(event, "")
        event_channel = guild.get_channel(int(channel_id)) if channel_id.isdigit() else None
        if not event_channel:
            event_channel = await guild.create_text_channel(name=event.lower())
            updated_channels[event] = str(event_channel.id)
    CONFIG["channels"] = updated_channels
    save_config(CONFIG)

async def post_ck_embed(ck_channel, clan_war):
    if clan_war:
        embed = Embed(
            title="📜 **Clan-Krieg Status**",
            description=f"Krieg gegen **{clan_war['opponent']['name']}**",
            color=0xFFD700
        )
        embed.add_field(name="⭐ Sterne", value=f"{clan_war['clan']['stars']} / {clan_war['opponent']['stars']}", inline=True)
        embed.add_field(name="⚔️ Angriffe", value=f"{clan_war['clan']['attacks']} / {clan_war['opponent']['attacks']}", inline=True)
        embed.add_field(name="🏰 Clan-Level", value=f"{clan_war['clan']['clanLevel']}", inline=True)
        embed.set_thumbnail(url=clan_war['clan']['badgeUrls']['small'])
        embed.set_footer(text="Clan-Krieg Status", icon_url=clan_war['opponent']['badgeUrls']['small'])
        await post_or_update_message(ck_channel, embed, "clan-war")
    else:
        embed = Embed(
            title="📜 **Clan-Krieg Status**",
            description="Es ist aktuell kein Clan-Krieg verfügbar.",
            color=0xFFD700
        )
        await post_or_update_message(ck_channel, embed, "clan-war")

async def post_cwl_embed(cwl_channel, cwl_data):
    """Postet CWL-Daten in einem Discord-Embed."""
    if not cwl_data:
        embed = Embed(
            title="🏆 **CWL Status**",
            description="Die CWL-Daten konnten nicht abgerufen werden.",
            color=0x1E90FF
        )
        await post_or_update_message(cwl_channel, embed, "clan-war-league")
        return

    # Verarbeite CWL-Daten
    opponent_name = cwl_data.get("opponent", {}).get("name", "Unbekannter Gegner")
    opponent_stars = cwl_data.get("opponent", {}).get("stars", 0)
    clan_stars = cwl_data.get("clan", {}).get("stars", 0)

    embed = Embed(
        title="🏆 **CWL Status**",
        description=f"Aktuelle Runde der CWL gegen **{opponent_name}**",
        color=0x1E90FF
    )
    embed.add_field(name="⭐ Sterne", value=f"{clan_stars} / {opponent_stars}", inline=True)
    embed.add_field(name="⚔️ Angriffe", value=f"{cwl_data['clan']['attacks']} / {cwl_data['opponent']['attacks']}", inline=True)
    embed.set_thumbnail(url=cwl_data['clan']['badgeUrls']['small'])

    await post_or_update_message(cwl_channel, embed, "clan-war-league")

async def post_clangames_embed(clangames_channel, clan_games_data):
    if not clan_games_data:
        embed = Embed(
            title="🎮 **Clangames Status**",
            description="Die Clan-Games-Daten konnten nicht abgerufen werden.",
            color=0x32CD32
        )
        await clangames_channel.send(embed=embed)
        return

    # Top-Spieler sortieren nach Punkten
    players = sorted(clan_games_data["players"], key=lambda x: x["points"], reverse=True)
    total_points = clan_games_data["total_points"]
    target_points = clan_games_data["target_points"]

    # Erstelle das Embed
    embed = Embed(
        title="🎮 **Clan-Games Fortschritt**",
        description=f"**Aktuelle Punkte:** {total_points} / {target_points}",
        color=0x32CD32
    )

    # Statusleiste für jeden Spieler
    for player in players:
        name = player["name"]
        points = player["points"]
        progress = int((points / 4000) * 20)  # 20 Zeichen lange Statusleiste
        bar = "█" * progress + "░" * (20 - progress)
        embed.add_field(
            name=f"👤 {name}",
            value=f"`{bar}`\nPunkte: {points} / 4000",
            inline=False
        )

    embed.set_footer(text="Clan-Games Statistik")
    await post_or_update_message(clangames_channel, embed, "clan-games")

async def post_event_updates():
    guild = discord.utils.get(client.guilds)

    # CK-Channel
    ck_channel = guild.get_channel(int(CONFIG["channels"]["CK"]))
    clan_war = fetch_clan_war()
    if clan_war and ck_channel:
        await post_ck_embed(ck_channel, clan_war)
    elif ck_channel:
        embed = Embed(
            title="📜 **Clan-Krieg Status**",
            description="Es ist aktuell kein Clan-Krieg verfügbar.",
            color=0xFFD700
        )
        await post_or_update_message(ck_channel, embed, "clan-war")

    # CWL-Channel
    cwl_channel = guild.get_channel(int(CONFIG["channels"]["CWL"]))
    cwl = fetch_cwl()
    if cwl and cwl_channel:
        await post_cwl_embed(cwl_channel, cwl)
    elif cwl_channel:
        embed = Embed(
            title="🏆 **CWL Status**",
            description="Die CWL-Daten konnten nicht abgerufen werden.",
            color=0x1E90FF
        )
        await post_or_update_message(cwl_channel, embed, "clan-war-league")

    # Clangames-Channel
    clangames_channel = guild.get_channel(int(CONFIG["channels"]["Clangames"]))
    clan_games_data = fetch_clan_games()
    if clangames_channel:
        await post_clangames_embed(clangames_channel, clan_games_data)

async def check_clan_membership():
    for user in verified_users.all():
        discord_id = user['discord_id']
        player_tag = user['player_tag']
        player_data = fetch_player_data(player_tag)

        if not player_data or not is_player_in_clan(player_data):
            guild = discord.utils.get(client.guilds)
            member = guild.get_member(int(discord_id))

            if member:
                try:
                    await guild.kick(member, reason="Benutzer hat den Clan verlassen.")
                    print(f"Kicked user {member.name} ({discord_id}) from the server.")
                except discord.Forbidden:
                    print(f"Cannot kick user {member.name} ({discord_id}) - insufficient permissions.")
                except discord.HTTPException as e:
                    print(f"Error kicking user {member.name} ({discord_id}): {e}")

            # Mark user data for deletion
            verified_users.update({'marked_for_deletion': True, 'marked_at': datetime.now(timezone.utc).isoformat()}, Query().discord_id == discord_id)

def cleanup_marked_data():
    threshold_date = datetime.utcnow() - timedelta(days=30)
    for user in verified_users.search(Query().marked_for_deletion == True):
        marked_at = datetime.fromisoformat(user.get('marked_at', datetime.now(timezone.utc).isoformat()))
        if marked_at < threshold_date:
            verified_users.remove(Query().discord_id == user['discord_id'])
            print(f"Deleted marked data for user: {user['discord_id']}")

def write_to_db(table, data, query=None):
    """Schreibt Daten in die db.json und formatiert sie automatisch."""
    if query:
        table.upsert(data, query)
    else:
        table.insert(data)

    # Formatiere die gesamte db.json
    db_file = "db.json"
    with open(db_file, "r", encoding="utf-8") as file:
        content = json.load(file)
    with open(db_file, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=4, ensure_ascii=False)

async def periodic_event_updates():
    while True:
        await post_event_updates()
        await asyncio.sleep(3600)  # Alle 60 Minuten aktualisieren

async def periodic_cleanup():
    while True:
        await check_clan_membership()
        cleanup_marked_data()
        await asyncio.sleep(86400)  # Einmal täglich

async def post_or_update_message(channel, embed, channel_name):
    """Bearbeitet eine bestehende Nachricht oder erstellt eine neue."""
    message_id = get_message_id(channel_name)

    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)
            return
        except discord.NotFound:
            # Nachricht existiert nicht mehr, erstelle eine neue
            pass

    # Neue Nachricht erstellen, wenn keine existiert
    new_message = await channel.send(embed=embed)
    save_message_id(channel_name, new_message.id)

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds)
    await ensure_roles(guild)
    await ensure_event_channels(guild)
    client.loop.create_task(periodic_event_updates())
    client.loop.create_task(periodic_cleanup())
    await tree.sync()
    print(f"Bot ist bereit! Eingeloggt als {client.user}")

@tree.command(name="verify", description="Verifiziere dich als Clanmitglied.")
async def verify(interaction: discord.Interaction, player_tag: str):
    await interaction.response.defer(ephemeral=True)

    # Spieler-Daten abrufen
    player_data = fetch_player_data(player_tag)
    if not player_data:
        await interaction.followup.send(
            "Fehler: Spieler konnte nicht gefunden werden. Bitte überprüfe deinen Spieler-Tag.",
            ephemeral=True
        )
        return

    # Prüfe, ob der Spieler im Clan ist
    if not is_player_in_clan(player_data):
        await interaction.followup.send(
            "Fehler: Du bist kein Mitglied des Clans oder der Spieler-Tag ist falsch.",
            ephemeral=True
        )
        return

    # Speichere die Benutzer-Daten in der Datenbank
    data = {
        'discord_id': str(interaction.user.id),
        'player_tag': player_tag,
        'player_name': player_data['name']
    }
    write_to_db(verified_users, data, Query().discord_id == str(interaction.user.id))

    # Synchronisiere die Rollen
    await update_roles(interaction, player_data)

async def update_roles(interaction, player_data):
    guild = interaction.guild
    if not guild:
        await interaction.followup.send(
            "Fehler: Dieser Befehl kann nur in einem Server verwendet werden.",
            ephemeral=True
        )
        return

    # Bestimme die Clan-Rolle des Spielers
    clan_role = player_data.get("role", "").lower()
    discord_role = get_discord_role(guild, clan_role)

    if not discord_role:
        await interaction.followup.send(
            f"Fehler: Keine entsprechende Discord-Rolle für die Clan-Rolle '{clan_role}' gefunden.",
            ephemeral=True
        )
        return

    try:
        # Entferne alle anderen zugeordneten Rollen
        current_roles = [role for role in interaction.user.roles if role.id in map(int, ROLE_MAPPING.values())]
        await interaction.user.remove_roles(*current_roles)

        # Weisen Sie die neue Rolle zu
        await interaction.user.add_roles(discord_role)
    except discord.Forbidden:
        await interaction.followup.send(
            "Fehler: Der Bot hat keine Berechtigung, diese Rolle zuzuweisen.",
            ephemeral=True
        )
        return
    except discord.HTTPException as e:
        await interaction.followup.send(
            f"Fehler beim Aktualisieren der Rolle: {e}",
            ephemeral=True
        )
        return

    await interaction.followup.send(
        f"Erfolgreich synchronisiert! Deine Discord-Rolle wurde als '{discord_role.name}' aktualisiert.",
        ephemeral=True
    )

@tree.command(name="delete_data", description="Lösche alle gespeicherten Daten und verlasse den Server.")
async def delete_data(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Fetch user data
    user_data = verified_users.get(Query().discord_id == str(interaction.user.id))
    if not user_data:
        await interaction.followup.send(
            "Es sind keine Daten zu deinem Account gespeichert.",
            ephemeral=True
        )
        return

    # Warn the user about consequences
    warning_message = (
        "**Warnung: Alle Daten werden gelöscht!**\n"
        "Wenn du fortfährst, werden folgende Aktionen durchgeführt:\n"
        "1. Alle gespeicherten Daten werden entfernt.\n"
        "2. Alle Rollen werden dir entzogen.\n"
        "3. Du wirst vom Server entfernt.\n"
        "\nWenn du den Server erneut betrittst, musst du den Verifizierungsprozess erneut durchlaufen."
    )
    await interaction.followup.send(warning_message, ephemeral=True)

    # Remove roles and kick user
    try:
        guild = interaction.guild
        if guild:
            # Remove all roles from the user
            roles_to_remove = [role for role in interaction.user.roles if role.id in map(int, ROLE_MAPPING.values())]
            await interaction.user.remove_roles(*roles_to_remove)

            # Kick the user
            await guild.kick(interaction.user, reason="Benutzer hat die Löschung seiner Daten beantragt.")

        # Delete user data from the database
        verified_users.remove(Query().discord_id == str(interaction.user.id))
    except Exception as e:
        await interaction.followup.send(
            f"Fehler beim Löschen der Daten: {e}",
            ephemeral=True
        )
        return

@tree.command(name="my_data", description="Zeige die gespeicherten Daten zu deinem Account.")
async def my_data(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Fetch user data
    user_data = verified_users.get(Query().discord_id == str(interaction.user.id))
    if not user_data:
        await interaction.followup.send(
            "Es sind keine Daten zu deinem Account gespeichert.",
            ephemeral=True
        )
        return

    # Display user data
    data_message = (
        f"**Deine gespeicherten Daten:**\n"
        f"- Discord-ID: {user_data['discord_id']}\n"
        f"- Spieler-Tag: {user_data['player_tag']}\n"
        f"- Spielername: {user_data['player_name']}\n"
    )
    await interaction.followup.send(data_message, ephemeral=True)

@tree.command(name="datenschutz", description="Zeige, welche Daten gespeichert werden.")
async def datenschutz(interaction: discord.Interaction):
    message = (
        "**Datenschutzinformationen**\n"
        "Dieser Bot speichert folgende Daten:\n"
        "- Deine Discord-ID\n"
        "- Deinen Clash of Clans Spieler-Tag\n"
        "- Deinen Spielernamen\n\n"
        "**Speicherdauer:**\n"
        "- Solange du im Clan bist, bleiben deine Daten gespeichert.\n"
        "- Wenn du den Clan verlässt, werden deine Daten markiert und nach 30 Tagen gelöscht.\n"
        "- Nach Nutzung des `/delete_data`-Befehls werden alle gespeicherten Daten sofort gelöscht.\n\n"
        "Du kannst jederzeit die Löschung deiner Daten beantragen oder den Datenschutzbeauftragten des Servers kontaktieren."
    )
    await interaction.response.send_message(message, ephemeral=True)

async def main():
    """Startet den Bot mit allen Cogs."""
    async with client:
        await client.start(DISCORD_TOKEN)

# Starte die asynchrone Hauptfunktion
if __name__ == "__main__":
    asyncio.run(main())
