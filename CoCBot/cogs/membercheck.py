from discord.ext import tasks, commands

import os
import certifi
import requests
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MemberCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_members.start()

    def cog_unload(self):
        self.check_members.cancel()

    @tasks.loop(hours=1)  # Task läuft alle 1 Stunde
    async def check_members(self):
        """Überprüft, ob Benutzer noch im Clan sind."""
        try:
            cursor = self.bot.db_connection.cursor()
            cursor.execute("SELECT discord_id, player_tag, warn_time FROM users")
            users = cursor.fetchall()

            for discord_id, player_tag, warn_time in users:
                role, clan_tag = self.get_clan_role(player_tag)

                if not role or not clan_tag:
                    # Benutzer ist nicht mehr im Clan
                    warn_time += 1

                    if warn_time >= 72:
                        # Benutzer nach 72 Stunden kicken
                        guild = self.bot.get_guild()  # Ersetze YOUR_GUILD_ID mit deiner Server-ID
                        member = guild.get_member(discord_id)
                        if member:
                            await guild.kick(member, reason="Nicht mehr im Clan (72 Stunden überschritten)")
                            logger.info(f"Benutzer {member.name} ({member.id}) wurde nach 72 Stunden entfernt.")

                        # Benutzer aus der Datenbank entfernen
                        cursor.execute("DELETE FROM users WHERE discord_id = %s", (discord_id,))
                        self.bot.db_connection.commit()

                    else:
                        # Warnzeit aktualisieren
                        cursor.execute("UPDATE users SET warn_time = %s WHERE discord_id = %s", (warn_time, discord_id))
                        self.bot.db_connection.commit()

                else:
                    # Benutzer ist noch im Clan, Warnzeit zurücksetzen
                    cursor.execute("UPDATE users SET warn_time = 0 WHERE discord_id = %s", (discord_id,))
                    self.bot.db_connection.commit()

            cursor.close()
        except Exception as e:
            logger.error(f"Fehler beim Überprüfen der Mitglieder: {e}")

    @check_members.before_loop
    async def before_check_members(self):
        """Warte, bis der Bot bereit ist."""
        await self.bot.wait_until_ready()

    def get_clan_role(self, player_tag: str) -> tuple:
        """Holt die Clan-Rolle und den Clan-Tag eines Spielers."""
        try:
            url = f"https://api.clashofclans.com/v1/players/{player_tag.replace('#', '%23')}"
            headers = {"Authorization": f"Bearer {os.getenv('COC_API_TOKEN')}"}
            response = requests.get(url, headers=headers, verify=certifi.where())
            if response.status_code != 200:
                logger.error(f"Fehler beim Abrufen der Spieler-Daten: {response.text}")
                return None, None
            player_data = response.json()
            role = player_data.get("role")
            clan_tag = player_data.get("clan", {}).get("tag")
            return role, clan_tag
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Clan-Rolle: {e}")
            return None, None


async def setup(bot):
    await bot.add_cog(MemberCheck(bot))
