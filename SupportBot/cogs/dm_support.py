import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import mysql.connector
from mysql.connector import Error
import random
import string

print("MySQL-Connector ist installiert und funktioniert!")

# Funktion zum Laden der Konfigurationsdatei
def load_config():
    """Lädt die Konfigurationsdatei dynamisch basierend auf dem Bot-Ordner."""
    config_path = os.path.join(os.path.dirname(__file__), "../config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
    with open(config_path, "r") as file:
        return json.load(file)

# Klasse für den DM-Support
class DMSupport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.support_channel_id = self.config.get("support_channel_id")
        if not self.support_channel_id:
            raise ValueError("Die Support-Kanal-ID fehlt in der config.json.")

        # MySQL-Verbindung einrichten
        self.db_connection = self.connect_to_database()
        self.initialize_database()

    def connect_to_database(self):
        """Stellt eine Verbindung zur MySQL-Datenbank her."""
        try:
            connection = mysql.connector.connect(
                host=self.config["db_host"],
                user=self.config["db_user"],
                password=self.config["db_password"],
                database=self.config["db_name"]
            )
            print("✅ Verbindung zur MySQL-Datenbank erfolgreich!")
            return connection
        except Error as e:
            print(f"❌ Fehler bei der Verbindung zur MySQL-Datenbank: {e}")
            raise

    def initialize_database(self):
        """Initialisiert die Tickets-Tabelle in der MySQL-Datenbank."""
        query = """
        CREATE TABLE IF NOT EXISTS tickets (
            id VARCHAR(7) PRIMARY KEY,
            user_id BIGINT NOT NULL,
            thread_id BIGINT,
            message TEXT NOT NULL,
            status ENUM('open', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        self.db_connection.commit()
        print("✅ Datenbank und Tabelle wurden erfolgreich initialisiert.")

    def generate_ticket_id(self):
        """Erstellt eine einzigartige alphanumerische Ticket-ID."""
        while True:
            ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            if not self.get_ticket_by_id(ticket_id):  # Sicherstellen, dass die ID einzigartig ist
                return ticket_id

    def create_ticket(self, user_id, thread_id, message):
        """Erstellt ein neues Ticket in der Datenbank."""
        ticket_id = self.generate_ticket_id()
        query = """
        INSERT INTO tickets (id, user_id, thread_id, message)
        VALUES (%s, %s, %s, %s)
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query, (ticket_id, user_id, thread_id, message))
        self.db_connection.commit()
        print(f"✅ Ticket erstellt: {ticket_id} für Benutzer-ID {user_id}")
        return ticket_id

    def get_open_ticket(self, user_id):
        """Holt ein offenes Ticket für den Benutzer."""
        query = """
        SELECT id, thread_id FROM tickets
        WHERE user_id = %s AND status = 'open'
        """
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute(query, (user_id,))
        ticket = cursor.fetchone()
        if ticket:
            print(f"ℹ️ Offenes Ticket gefunden: {ticket['id']} für Benutzer-ID {user_id}")
        else:
            print(f"ℹ️ Kein offenes Ticket für Benutzer-ID {user_id}")
        return ticket

    def get_ticket_by_id(self, ticket_id):
        """Holt ein Ticket anhand seiner ID."""
        query = """
        SELECT * FROM tickets WHERE id = %s
        """
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute(query, (ticket_id,))
        return cursor.fetchone()

    def close_ticket(self, ticket_id):
        """Schließt ein Ticket."""
        query = """
        UPDATE tickets SET status = 'closed'
        WHERE id = %s
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query, (ticket_id,))
        self.db_connection.commit()
        print(f"✅ Ticket geschlossen: {ticket_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Verarbeitet Nachrichten aus Threads und DMs."""
        if message.author.bot:
            return  # Ignoriere Nachrichten vom Bot selbst

        # **Fall 1: Nachricht stammt aus einem Thread**
        if isinstance(message.channel, discord.Thread):
            print(f"🔄 Nachricht in Thread erkannt: {message.channel.id}")
            query = """
            SELECT user_id FROM tickets WHERE thread_id = %s AND status = 'open'
            """
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute(query, (message.channel.id,))
            ticket = cursor.fetchone()

            if ticket:
                user_id = ticket["user_id"]
                try:
                    # Benutzer direkt von Discord abrufen
                    user = await self.bot.fetch_user(user_id)
                    if user:
                        # Nachricht an den Benutzer senden
                        await user.send(f"💬 **Antwort auf dein Ticket:**\n{message.content}")
                        await message.add_reaction("✅")  # Erfolgssymbol hinzufügen
                        print(f"✉️ Nachricht erfolgreich an Benutzer {user_id} gesendet.")
                    else:
                        await message.channel.send("❌ Benutzer konnte nicht abgerufen werden.")
                        print(f"❌ Benutzer-ID {user_id} nicht gefunden.")
                except discord.NotFound:
                    await message.channel.send("❌ Benutzer existiert nicht mehr.")
                    print(f"❌ Benutzer-ID {user_id} wurde gelöscht oder existiert nicht.")
                except discord.Forbidden:
                    await message.channel.send("❌ Benutzer hat DMs deaktiviert.")
                    print(f"❌ Benutzer-ID {user_id} hat DMs deaktiviert.")
            else:
                await message.channel.send("❌ Kein zugehöriges Ticket gefunden.")
                print(f"❌ Kein Ticket für Thread-ID {message.channel.id} gefunden.")
            return

        # **Fall 2: Nachricht stammt aus einer DM**
        if isinstance(message.channel, discord.DMChannel):
            print(f"📩 DM erhalten von {message.author}: {message.content}")
            open_ticket = self.get_open_ticket(message.author.id)
            if open_ticket:
                # Nachricht in bestehendem Thread weiterleiten
                thread_id = open_ticket["thread_id"]
                thread = self.bot.get_channel(thread_id)
                if thread:
                    await thread.send(f"📩 **Neue Nachricht von {message.author}:**\n{message.content}")
                    await message.channel.send("Deine Nachricht wurde deinem bestehenden Ticket hinzugefügt.")
                    print(f"Nachricht im bestehenden Ticket-Thread {thread_id} weitergeleitet.")
                else:
                    await message.channel.send(
                        "Es gibt ein Problem mit deinem bestehenden Ticket. Bitte kontaktiere den Support erneut.")
                    print(f"Fehler: Thread mit ID {thread_id} nicht gefunden.")
                return

            # Neues Ticket erstellen
            support_channel = self.bot.get_channel(self.support_channel_id)
            if not support_channel:
                print(f"❌ Support-Kanal mit der ID {self.support_channel_id} nicht gefunden.")
                return

            thread = await support_channel.create_thread(name=f"Ticket-{message.author.name}",
                                                         type=discord.ChannelType.public_thread)
            ticket_id = self.create_ticket(message.author.id, thread.id, message.content)

            await thread.send(f"📩 **Neues Ticket von {message.author}:**\n{message.content}")
            await message.channel.send(
                f"Dein Ticket wurde erstellt. Ticket-ID: {ticket_id}. Ein Supporter wird sich melden.")
            print(f"📋 Neues Ticket erstellt: {ticket_id} für Benutzer {message.author} (Thread-ID: {thread.id})")

    async def handle_dm_message(self, message):
        """Behandelt eingehende DMs."""
        open_ticket = self.get_open_ticket(message.author.id)
        if open_ticket:
            thread_id = open_ticket["thread_id"]
            thread = self.bot.get_channel(thread_id)
            if thread:
                await thread.send(f"📩 **Neue Nachricht von {message.author}:**\n{message.content}")
                await message.channel.send("ℹ️ Deine Nachricht wurde deinem bestehenden Ticket hinzugefügt.")
                print(f"ℹ️ Nachricht zu bestehendem Ticket {open_ticket['id']} hinzugefügt.")
            else:
                await message.channel.send("❌ Problem mit deinem bestehenden Ticket.")
            return

        # Neues Ticket erstellen
        support_channel = self.bot.get_channel(self.support_channel_id)
        if not support_channel:
            print(f"❌ Support-Kanal mit der ID {self.support_channel_id} nicht gefunden.")
            return

        thread = await support_channel.create_thread(name=f"Ticket-{message.author.name}", type=discord.ChannelType.public_thread)
        ticket_id = self.create_ticket(message.author.id, thread.id, message.content)

        await thread.send(f"📩 **Neues Ticket von {message.author}:**\n{message.content}")
        await message.channel.send(f"✅ Dein Ticket wurde erstellt. Ticket-ID: {ticket_id}. Ein Supporter wird sich melden.")
        print(f"✅ Neues Ticket {ticket_id} für Benutzer-ID {message.author.id} erstellt.")

    @app_commands.command(name="close_ticket")
    @commands.has_permissions(manage_messages=True)
    async def close_ticket_command(self, ctx, ticket_id: str):
        """Schließt ein Ticket."""
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            await ctx.send(f"❌ Kein Ticket mit der ID {ticket_id} gefunden.")
            print(f"❌ Kein Ticket mit der ID {ticket_id} gefunden.")
            return

        self.close_ticket(ticket_id)
        await ctx.send(f"✅ Ticket {ticket_id} wurde geschlossen.")
        print(f"✅ Ticket {ticket_id} geschlossen.")
        await self.bot.tree.sync()
        print(f"[DEBUG] Aktuelle Slash-Commands: {self.bot.tree.get_commands()}")


# Setup-Funktion für den Bot
async def setup(bot):
    cog = DMSupport(bot)
    await bot.add_cog(cog)
