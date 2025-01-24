import asyncio
from dotenv import load_dotenv
import os
from CoCBot.clashofclans_bot import ClashOfClansBot
from SupportBot.support_bot import SupportBot
from TwitchNotifier.twitch_bot import TwitchBot
import sys

# Füge den spezifischen Cogs-Pfad zum Python-Pfad hinzu
bot_cogs_path = os.path.join(os.path.dirname(__file__), "cogs")  # Passe "cogs" an, wenn dein Ordner anders heißt
if bot_cogs_path not in sys.path:
    sys.path.append(bot_cogs_path)

# Umgebungsvariablen laden
load_dotenv()

def get_bot_token(bot_name):
    """
    Hilfsfunktion, um Bot-Tokens aus den Umgebungsvariablen zu laden.
    :param bot_name: Name des Bots
    :return: Token als String
    """
    token = os.getenv(f"DISCORD_TOKEN_{bot_name.upper()}")
    if not token:
        raise ValueError(f"Bot-Token für {bot_name} nicht in der .env-Datei gefunden.")
    return token

async def main():
    """
    Hauptfunktion, die alle Bots initialisiert und startet.
    """
    try:
        # Bots initialisieren
        coc_bot = ClashOfClansBot(get_bot_token("CLASH"))
        support_bot = SupportBot(get_bot_token("SUPPORT"))
        twitch_bot = TwitchBot(get_bot_token("TWITCH"))

        # Alle Bots parallel starten
        await asyncio.gather(
            coc_bot.start(coc_bot.token),
            support_bot.start(support_bot.token),
            twitch_bot.start(twitch_bot.token)
        )
    except Exception as e:
        print(f"Fehler beim Starten der Bots: {e}")

if __name__ == "__main__":
    asyncio.run(main())
