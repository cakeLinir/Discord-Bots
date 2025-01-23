import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

TOTAL_POINTS = 50000
MAX_PLAYER_POINTS = 4000


import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

TOTAL_POINTS = 50000
MAX_PLAYER_POINTS = 4000


class ClanSpiele(commands.Cog):
    """Cog zur Verwaltung der Clanspiele."""

    def __init__(self, bot):
        self.bot = bot

    def get_event_channel(self) -> discord.TextChannel:
        """Holt den Clanspiele-Kanal aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT channel_id FROM event_channels WHERE event_type = 'clanspiele'
            """)
            result = cursor.fetchone()
            cursor.close()
            if result:
                return self.bot.get_channel(result[0])
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Clanspiele-Channels: {e}")
            return None

    def get_clanspiele_data(self) -> dict:
        """Holt die aktuellen Clanspiele-Daten aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT id, start_time, end_time, progress, message_id, channel_id
                FROM clanspiele_data ORDER BY id DESC LIMIT 1
            """)
            result = cursor.fetchone()
            cursor.close()
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

    def get_player_points(self, clanspiele_id: int) -> dict:
        """Holt die Punkte aller Spieler aus der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                SELECT discord_id, coc_name, points FROM clanspiele_players
                WHERE clanspiele_id = %s
            """, (clanspiele_id,))
            result = cursor.fetchall()
            cursor.close()
            return [{"discord_id": row[0], "coc_name": row[1], "points": row[2]} for row in result]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spielerpunkte: {e}")
            return []

    def update_player_points(self, clanspiele_id: int, discord_id: int, coc_name: str, points: int):
        """Aktualisiert die Punkte eines Spielers in der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO clanspiele_players (clanspiele_id, discord_id, coc_name, points)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE coc_name = VALUES(coc_name), points = points + VALUES(points)
            """, (clanspiele_id, discord_id, coc_name, points))
            self.bot.db_connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Spielerpunkte: {e}")

    def build_embed(self, clanspiele_data: dict, player_points: list) -> discord.Embed:
        """Erstellt ein Embed für die Clanspiele."""
        total_points = clanspiele_data["progress"]
        percentage = min(100, total_points / TOTAL_POINTS * 100)

        embed = discord.Embed(
            title="Clanspiele Fortschritt",
            description=f"Gesamtfortschritt: {total_points} / {TOTAL_POINTS} Punkte",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Startzeit", value=clanspiele_data["start_time"], inline=True)
        embed.add_field(name="Endzeit", value=clanspiele_data["end_time"], inline=True)

        # Fortschrittsbalken für den Gesamtfortschritt
        filled_length = int(20 * total_points // TOTAL_POINTS)
        progress_bar = "█" * filled_length + "░" * (20 - filled_length)
        embed.add_field(name="Fortschrittsbalken", value=f"[{progress_bar}] {percentage:.2f}%", inline=False)

        # Spielerfortschritt
        player_details = ""
        for player in player_points:
            member = self.bot.get_user(player["discord_id"])
            player_bar = "█" * int(20 * player["points"] / MAX_PLAYER_POINTS) + "░" * (20 - int(20 * player["points"] / MAX_PLAYER_POINTS))
            player_details += f"**{player['coc_name']}** ({member.name if member else 'Unbekannt'}): {player['points']} Punkte [{player_bar}]\n"

        embed.add_field(name="Spieler Fortschritt", value=player_details or "Keine Spielerpunkte verfügbar", inline=False)
        embed.set_footer(text="Clash of Clans Bot - Clan-Spiele")
        return embed

    @app_commands.command(name="update_clanspiele", description="Aktualisiert den Fortschritt eines Spielers.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_clanspiele(self, interaction: discord.Interaction, member: discord.Member, coc_name: str, points: int):
        """Aktualisiert die Punkte eines Spielers und das Clanspiele-Embed."""
        try:
            clanspiele_data = self.get_clanspiele_data()
            if not clanspiele_data:
                await interaction.response.send_message("Keine aktiven Clanspiele gefunden.", ephemeral=True)
                return

            self.update_player_points(clanspiele_data["id"], member.id, coc_name, points)

            # Neuen Gesamtfortschritt berechnen
            player_points = self.get_player_points(clanspiele_data["id"])
            total_points = sum(player["points"] for player in player_points)

            # Datenbank aktualisieren
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                UPDATE clanspiele_data
                SET progress = %s
                WHERE id = %s
            """, (total_points, clanspiele_data["id"]))
            self.bot.db_connection.commit()
            cursor.close()

            # Embed aktualisieren
            channel = self.bot.get_channel(clanspiele_data["channel_id"])
            if channel:
                message = await channel.fetch_message(clanspiele_data["message_id"])
                embed = self.build_embed(clanspiele_data, player_points)
                await message.edit(embed=embed)

            await interaction.response.send_message(f"Punkte von {member.name} wurden aktualisiert.", ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Clanspiele: {e}")
            await interaction.response.send_message("Fehler beim Aktualisieren der Clanspiele.", ephemeral=True)
    
    @app_commands.command(name="add_clanspiele_data", description="Fügt neue Clanspiele-Daten hinzu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_clanspiele_data(self, interaction: discord.Interaction, start_time: str, end_time: str):
        """Fügt neue Clanspiele-Daten hinzu und erstellt ein Embed."""
        try:
            # Konvertiere Datumsangaben ins MySQL-kompatible Format
            try:
                start_time_formatted = datetime.strptime(start_time, "%d.%m.%Y").strftime("%Y-%m-%d %H:%M:%S")
                end_time_formatted = datetime.strptime(end_time, "%d.%m.%Y").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                await interaction.response.send_message(
                    "Ungültiges Datum. Bitte im Format TT.MM.JJJJ angeben.", ephemeral=True
                )
                return

            # Überprüfe, ob ein Event-Kanal für Clanspiele vorhanden ist
            channel = self.get_event_channel()
            if not channel:
                await interaction.response.send_message(
                    "Kein Clanspiele-Kanal festgelegt. Bitte einen Kanal mit `/set_event_channel` setzen.",
                    ephemeral=True
                )
                return

            # Datenbankeintrag erstellen
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO clanspiele_data (start_time, end_time, progress, message_id, channel_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (start_time_formatted, end_time_formatted, 0, None, channel.id))
            clanspiele_id = cursor.lastrowid  # ID des neuen Datensatzes
            self.bot.db_connection.commit()

            # Initiales Embed erstellen
            embed = discord.Embed(
                title="Clanspiele gestartet!",
                description="Neues Clan-Spiel wurde erstellt. Fortschritt wird hier angezeigt.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Startzeit", value=start_time, inline=True)
            embed.add_field(name="Endzeit", value=end_time, inline=True)
            embed.add_field(name="Gesamtfortschritt", value=f"0 / {TOTAL_POINTS} Punkte", inline=False)
            embed.add_field(name="Fortschrittsbalken", value=f"[{'░' * 20}] 0.00%", inline=False)
            embed.add_field(name="Spieler Fortschritt", value="Noch keine Spielerpunkte verfügbar.", inline=False)
            embed.set_footer(text="Clash of Clans Bot - Clan-Spiele")

            # Embed im Kanal posten
            message = await channel.send(embed=embed)

            # Nachricht-ID und Kanal-ID in der Datenbank aktualisieren
            cursor.execute("""
                UPDATE clanspiele_data
                SET message_id = %s, channel_id = %s
                WHERE id = %s
            """, (message.id, channel.id, clanspiele_id))
            self.bot.db_connection.commit()
            cursor.close()

            await interaction.response.send_message(
                f"Clanspiele-Daten erfolgreich hinzugefügt und im Kanal {channel.mention} gepostet.", ephemeral=True
            )
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Clanspiele-Daten: {e}")
            await interaction.response.send_message("Fehler beim Hinzufügen der Clanspiele-Daten.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ClanSpiele(bot))
