import os
import discord
from typing import Any, Optional
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import requests
import logging
import math
import asyncio

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TOTAL_POINTS = 50000
MAX_PLAYER_POINTS = 4000


class Clanspiele(commands.Cog):
    """Cog zur Verwaltung der Clanspiele."""

    def __init__(self, bot):
        self.bot = bot

    def get_player_name(self, player_tag: str) -> str:
        """Holt den Spielernamen basierend auf dem Spieler-Tag."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("SELECT coc_name FROM users WHERE player_tag = %s", (player_tag,))
                result = cursor.fetchone()
            return result[0] if result else "Unbekannt"
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Spielernamens: {e}")
            return "Unbekannt"

    def get_event_channel(self) -> Optional[discord.TextChannel]:
        """Holt den Channel für die Clan-Spiele aus der Datenbank."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("SELECT channel_id FROM event_channels WHERE event_type = 'clanspiele'")
                result = cursor.fetchone()
            return self.bot.get_channel(result[0]) if result else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Clanspiele-Channels: {e}")
            return None

    def get_clanspiele_data(self) -> Optional[dict[str, Any]]:
        """Holt die aktuellen Clan-Spiele-Daten aus der Datenbank."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                SELECT id, start_time, end_time, progress, message_id, channel_id
                FROM clanspiele ORDER BY id DESC LIMIT 1
                """)
                result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "start_time": result[1],
                    "end_time": result[2],
                    "progress": result[3],
                    "message_id": result[4],
                    "channel_id": result[5],
                }
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clanspiele-Daten: {e}")
            return None

    def get_user_data(self, player_tag: str) -> Optional[dict[str, Any]]:
        """Holt den Spielernamen und die Discord-ID anhand des Spieler-Tags aus der Datenbank."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("SELECT coc_name, discord_id FROM users WHERE player_tag = %s", (player_tag,))
                result = cursor.fetchone()
            return {"coc_name": result[0], "discord_id": result[1]} if result else None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzerdaten: {e}")
            return None

    def get_player_points(self, clanspiele_id: int) -> dict[str, int]:
        """Holt die Punktzahlen aller Spieler aus der Datenbank."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("SELECT coc_name, points FROM clanspiele_players WHERE clanspiele_id = %s", (clanspiele_id,))
                result = cursor.fetchall()
            return {coc_name: points for coc_name, points in result}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spielerpunkte: {e}")
            return {}

    def update_player_points(self, clanspiele_id: int, player_tag: str, coc_name: str, points: int):
        """Aktualisiert die Punktzahlen eines Spielers in der Datenbank."""
        try:
            user_data = self.get_user_data(player_tag)  # Holt coc_name und discord_id
            discord_id = user_data.get(
                "discord_id") if user_data else None  # Kann None sein, wenn Spieler nicht auf Discord ist

            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO clanspiele_players (clanspiele_id, player_tag, coc_name, points, discord_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE points = VALUES(points)
                """, (clanspiele_id, player_tag, coc_name, points, discord_id))
            self.bot.db_connection.commit()

            # Gesamtpunkte berechnen und aktualisieren
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(points) FROM clanspiele_players WHERE clanspiele_id = %s
                """, (clanspiele_id,))
                total_progress = cursor.fetchone()[0] or 0

                cursor.execute("""
                    UPDATE clanspiele SET progress = %s WHERE id = %s
                """, (total_progress, clanspiele_id))
            self.bot.db_connection.commit()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Spielerpunkte: {e}")

    def create_progress_bar(self, current: int, maximum: int) -> str:
        """Generates a progress bar."""
        filled_length = int(20 * current / maximum)
        return "█" * filled_length + "░" * (20 - filled_length)

    def build_embed(self, clanspiele_data: dict, player_points: dict, page: int = 1,
                    players_per_page: int = 10) -> discord.Embed:
        """Erstellt ein Embed für die Clan-Spiele mit mehreren Seiten."""
        total_points = clanspiele_data["progress"]
        percentage = min(100, total_points / TOTAL_POINTS * 100)

        embed = discord.Embed(
            title="Clan-Spiele Fortschritt",
            description=f"Gesamtfortschritt: {total_points} / {TOTAL_POINTS} Punkte",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Startzeit", value=clanspiele_data["start_time"], inline=True)
        embed.add_field(name="Endzeit", value=clanspiele_data["end_time"], inline=True)

        # Fortschrittsbalken
        progress_bar = self.create_progress_bar(total_points, TOTAL_POINTS)
        embed.add_field(name="Fortschrittsbalken", value=f"[{progress_bar}] {percentage:.2f}%", inline=False)

        # Spieler-Daten für die aktuelle Seite
        player_data = sorted(player_points.items(), key=lambda item: item[1], reverse=True)
        total_pages = math.ceil(len(player_data) / players_per_page)
        start_index = (page - 1) * players_per_page
        end_index = start_index + players_per_page
        players_on_page = player_data[start_index:end_index]

        # Separate Spalten für Spieler, Punkte und Balken
        player_column = "\n".join([f"{name}" for name, _ in players_on_page])
        points_column = "\n".join([f"{points}" for _, points in players_on_page])
        bar_column = "\n".join(
            [f"[{self.create_progress_bar(points, MAX_PLAYER_POINTS)}]" for _, points in players_on_page])

        if players_on_page:
            embed.add_field(name="Spieler", value=player_column, inline=True)
            embed.add_field(name="Punkte", value=points_column, inline=True)
            embed.add_field(name="Balken", value=bar_column, inline=True)
        else:
            embed.add_field(name="Keine Spieler verfügbar", value="Noch keine Punkte eingetragen.", inline=False)

        # Footer mit Seitenzahl
        embed.set_footer(text=f"Seite {page}/{total_pages} | Clash of Clans Bot - Clan-Spiele")
        return embed

    async def update_clanspiele_embed(self, clanspiele_id: int, page: int = 1):
        """Aktualisiert das Clan-Spiele-Embed."""
        clanspiele_data = self.get_clanspiele_data()
        if not clanspiele_data or clanspiele_data["id"] != clanspiele_id:
            logger.error("Clanspiele-Daten stimmen nicht überein.")
            return

        player_points = self.get_player_points(clanspiele_id)
        total_points = sum(player_points.values())

        # Fortschritt in der Datenbank aktualisieren
        with self.bot.db_connection.cursor() as cursor:
            cursor.execute("""
                UPDATE clanspiele
                SET progress = %s
                WHERE id = %s
            """, (total_points, clanspiele_id))
        self.bot.db_connection.commit()

        # Embed aktualisieren
        embed = self.build_embed(clanspiele_data, player_points, page)
        channel = self.bot.get_channel(clanspiele_data["channel_id"])
        if not channel:
            logger.error("Clanspiele-Kanal nicht gefunden.")
            return

        try:
            message = await channel.fetch_message(clanspiele_data["message_id"])
            if message:
                await message.edit(embed=embed)
        except discord.NotFound:
            logger.error(f"Nachricht mit ID {clanspiele_data['message_id']} nicht gefunden.")

    @app_commands.command(name="start_clanspiele", description="Startet ein neues Clanspiel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_clanspiele(self, interaction: discord.Interaction, start_time: str, end_time: str):
        """Startet ein neues Clanspiel."""
        try:
            # Datenbank aktualisieren
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO clanspiele (start_time, end_time) VALUES (%s, %s)
                """, (start_time, end_time))
                clanspiele_id = cursor.lastrowid
            self.bot.db_connection.commit()

            logger.info(f"Neue Clan-Spiele gestartet mit Startzeit {start_time} und Endzeit {end_time}.")

            # Embed posten
            clanspiele_data = self.get_clanspiele_data()
            embed = self.build_embed(clanspiele_data, {})
            channel = self.get_event_channel()
            if not channel:
                await interaction.response.send_message("Clanspiele-Kanal nicht gefunden.", ephemeral=True)
                return
            message = await channel.send(embed=embed)

            # Nachricht speichern
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE clanspiele
                    SET message_id = %s, channel_id = %s
                    WHERE id = %s
                """, (message.id, channel.id, clanspiele_id))
            self.bot.db_connection.commit()

            await interaction.response.send_message("Clanspiele erfolgreich gestartet.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Starten der Clanspiele: {e}")
            await interaction.response.send_message("Fehler beim Starten der Clanspiele.", ephemeral=True)

    @app_commands.command(name="update_points", description="Aktualisiert die Punkte eines Spielers.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_points(self, interaction: discord.Interaction, player_tag: str, points: int):
        """Aktualisiert die Punkte eines Spielers."""
        try:
            clanspiele_data = self.get_clanspiele_data()
            if not clanspiele_data:
                await interaction.response.send_message("Keine aktiven Clan-Spiele gefunden.", ephemeral=True)
                return

            user_data = self.get_user_data(player_tag)
            if not user_data:
                await interaction.response.send_message(f"Spielertag {player_tag} nicht gefunden.", ephemeral=True)
                return

            coc_name = user_data["coc_name"]
            self.update_player_points(clanspiele_data["id"], player_tag, coc_name, points)

            await self.update_clanspiele_embed(clanspiele_data["id"])
            await interaction.response.send_message(f"Punkte von {coc_name} wurden auf {points} aktualisiert.",
                                                    ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Punkte: {e}")
            await interaction.response.send_message("Fehler beim Aktualisieren der Punkte.", ephemeral=True)

    @app_commands.command(name="update_embed", description="Aktualisiert das Clan-Spiele-Embed.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_embed(self, interaction: discord.Interaction, page: int = 1):
        """Aktualisiert das Embed basierend auf gespeicherten Daten."""
        try:
            clanspiele_data = self.get_clanspiele_data()
            if not clanspiele_data:
                await interaction.response.send_message("Keine aktiven Clan-Spiele gefunden.", ephemeral=True)
                return

            await self.update_clanspiele_embed(clanspiele_data["id"], page)
            await interaction.response.send_message(f"Das Clan-Spiele-Embed wurde auf Seite {page} aktualisiert.",
                                                    ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Clan-Spiele-Embeds: {e}")
            await interaction.response.send_message("Fehler beim Aktualisieren des Embeds.", ephemeral=True)

    async def post_initial_embed(self, clanspiele_id: int):
        """Postet das initiale Embed für die Clan-Spiele."""
        clanspiele_data = self.get_clanspiele_data()
        if not clanspiele_data:
            logger.error("Keine Clan-Spiele-Daten gefunden.")
            return

        embed = self.build_embed(clanspiele_data, {})
        channel = self.get_event_channel()
        if not channel:
            logger.error("Clanspiele-Kanal nicht gefunden.")
            return

        message = await channel.send(embed=embed)
        with self.bot.db_connection.cursor() as cursor:
            cursor.execute("""
                UPDATE clanspiele
                SET message_id = %s, channel_id = %s
                WHERE id = %s
            """, (message.id, channel.id, clanspiele_id))
        self.bot.db_connection.commit()

    def save_embed_message(self, clanspiele_id: int, message_id: int, channel_id: int):
        """Speichert die Embed-Nachricht in der Datenbank."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE clanspiele
                    SET message_id = %s, channel_id = %s
                    WHERE id = %s
                """, (message_id, channel_id, clanspiele_id))
            self.bot.db_connection.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Embed-Nachricht: {e}")

    def fetch_player_name(self, player_tag: str) -> Optional[str]:
        """Holt den Spielernamen von der Clash of Clans API."""
        try:
            coc_api_token = os.getenv('COC_API_TOKEN')
            if not coc_api_token:
                logger.error("Clash of Clans API token is missing.")
                return None
            url = f"https://api.clashofclans.com/v1/players/{player_tag.replace('#', '%23')}"

            headers = {"Authorization": f"Bearer {coc_api_token}"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json().get("name")
            logger.error(f"API-Fehler beim Abrufen des Spielernamens für Tag {player_tag}. "
                         f"Status: {response.status_code}, Antwort: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Spielernamens: {e}")
            return None

    def save_embed_state(self, clanspiele_id: int, message_id: int, sort_order: str, current_page: int):
        """Speichert den Status des interaktiven Embeds."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE clanspiele
                    SET message_id = %s, sort_order = %s, current_page = %s
                    WHERE id = %s
                """, (message_id, sort_order, current_page, clanspiele_id))
            self.bot.db_connection.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Embed-Status: {e}")

    async def interactive_embed(self, interaction: Optional[discord.Interaction], clanspiele_id: int,
                                message: Optional[discord.Message] = None, sort_order: str = "desc",
                                current_page: int = 1):
        """Erstellt ein interaktives Embed mit persistenter Navigation."""
        clanspiele_data = self.get_clanspiele_data()
        if not clanspiele_data or clanspiele_data["id"] != clanspiele_id:
            logger.error("Clanspiele-Daten stimmen nicht überein.")
            if interaction:
                await interaction.response.send_message("Fehler: Clanspiele-Daten stimmen nicht überein.",
                                                        ephemeral=True)
            return

        player_points = self.get_player_points(clanspiele_id)
        total_pages = max(1, (len(player_points) + 9) // 10)

        def sort_players(players, order):
            return sorted(players.items(), key=lambda item: item[1], reverse=(order == "desc"))

        async def update_embed_message():
            sorted_points = sort_players(player_points, sort_order)
            paginated_points = dict(list(sorted_points)[(current_page - 1) * 10: current_page * 10])
            embed = self.build_embed(clanspiele_data, paginated_points)
            await message.edit(embed=embed)
            self.save_embed_state(clanspiele_id, message.id, sort_order, current_page)

        if not message and interaction:
            sorted_points = sort_players(player_points, sort_order)
            paginated_points = dict(list(sorted_points)[:10])
            embed = self.build_embed(clanspiele_data, paginated_points)
            channel = interaction.channel
            if not channel:
                await interaction.response.send_message("Fehler: Kanal nicht gefunden.", ephemeral=True)
                return

            message = await channel.send(embed=embed)
            await interaction.response.send_message("Interaktive Clan-Spiele-Navigation gestartet.", ephemeral=True)
            self.save_embed_state(clanspiele_id, message.id, sort_order, current_page)

        reactions = {"⬅️": "prev", "➡️": "next", "🔼": "asc", "🔽": "desc", "❌": "stop"}
        for emoji in reactions.keys():
            await message.add_reaction(emoji)

        def check(reaction, user):
            return (
                    user == (interaction.user if interaction else None)
                    and str(reaction.emoji) in reactions
                    and reaction.message.id == message.id
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                action = reactions[str(reaction.emoji)]

                if action == "prev" and current_page > 1:
                    current_page -= 1
                    await update_embed_message()
                elif action == "next" and current_page < total_pages:
                    current_page += 1
                    await update_embed_message()
                elif action == "asc":
                    sort_order = "asc"
                    current_page = 1
                    await update_embed_message()
                elif action == "desc":
                    sort_order = "desc"
                    current_page = 1
                    await update_embed_message()
                elif action == "stop":
                    await message.clear_reactions()
                    break

                await message.remove_reaction(reaction.emoji, user)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                break

    async def reinitialize_embeds(self):
        """Lädt interaktive Embeds nach einem Neustart neu."""
        try:
            with self.bot.db_connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, message_id, channel_id, sort_order, current_page
                    FROM clanspiele WHERE message_id IS NOT NULL
                """)
                embeds = cursor.fetchall()

            for clanspiele_id, message_id, channel_id, sort_order, current_page in embeds:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Kanal mit ID {channel_id} nicht gefunden.")
                    continue

                try:
                    message = await channel.fetch_message(message_id)
                    reactions = ["⬅️", "➡️", "🔼", "🔽", "❌"]
                    for emoji in reactions:
                        await message.add_reaction(emoji)

                    # Starte die Interaktion erneut
                    await self.interactive_embed(None, clanspiele_id, message, sort_order, current_page)
                except discord.NotFound:
                    logger.warning(f"Nachricht mit ID {message_id} nicht gefunden.")
                except Exception as e:
                    logger.error(f"Fehler bei der Reinitialisierung: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Laden gespeicherter Embeds: {e}")

    @app_commands.command(name="interactive_clanspiele", description="Startet ein interaktives Clan-Spiele-Embed.")
    @app_commands.checks.has_permissions(administrator=False)
    async def interactive_clanspiele(self, interaction: discord.Interaction):
        """Startet ein interaktives Embed für die Clan-Spiele."""
        try:
            clanspiele_data = self.get_clanspiele_data()
            if not clanspiele_data:
                await interaction.response.send_message("Keine aktiven Clan-Spiele gefunden.", ephemeral=True)
                return

            await self.interactive_embed(interaction, clanspiele_data["id"])
        except Exception as e:
            logger.error(f"Fehler beim Starten des interaktiven Embeds: {e}")
            await interaction.response.send_message("Fehler beim Starten des interaktiven Embeds.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Clanspiele(bot))
