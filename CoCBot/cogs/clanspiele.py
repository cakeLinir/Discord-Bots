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
                SELECT discord_id, points FROM clanspiele_players
                WHERE clanspiele_id = %s
            """, (clanspiele_id,))
            result = cursor.fetchall()
            cursor.close()
            return {discord_id: points for discord_id, points in result}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spielerpunkte: {e}")
            return {}

    def update_player_points(self, clanspiele_id: int, discord_id: int, points: int):
        """Aktualisiert die Punkte eines Spielers in der Datenbank."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("""
                INSERT INTO clanspiele_players (clanspiele_id, discord_id, points)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE points = VALUES(points)
            """, (clanspiele_id, discord_id, points))
            self.bot.db_connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Spielerpunkte: {e}")

    def build_embed(self, clanspiele_data: dict, player_points: dict) -> discord.Embed:
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
        for discord_id, points in player_points.items():
            member = self.bot.get_user(discord_id)
            player_bar = "█" * int(20 * points / MAX_PLAYER_POINTS) + "░" * (20 - int(20 * points / MAX_PLAYER_POINTS))
            player_details += f"**{member.name if member else discord_id}:** {points} Punkte [{player_bar}]\n"
        embed.add_field(name="Spieler Fortschritt", value=player_details or "Keine Spielerpunkte verfügbar", inline=False)
        embed.set_footer(text="Clash of Clans Bot - Clan-Spiele")
        return embed

    @app_commands.command(name="update_clanspiele", description="Aktualisiert den Fortschritt eines Spielers.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_clanspiele(self, interaction: discord.Interaction, member: discord.Member, points: int):
        """Aktualisiert die Punkte eines Spielers und das Clanspiele-Embed."""
        try:
            clanspiele_data = self.get_clanspiele_data()
            if not clanspiele_data:
                await interaction.response.send_message("Keine aktiven Clanspiele gefunden.", ephemeral=True)
                return

            self.update_player_points(clanspiele_data["id"], member.id, points)

            # Neuen Gesamtfortschritt berechnen
            player_points = self.get_player_points(clanspiele_data["id"])
            total_points = sum(player_points.values())

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


async def setup(bot):
    await bot.add_cog(ClanSpiele(bot))
