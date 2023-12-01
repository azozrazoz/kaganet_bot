import nextcord
from nextcord.ext import commands
import logging
import config

from cogs.music_cog import MusicCog
from cogs.error_cog import ErrorCog
from cogs.user_cog import UserCog

logger = logging.getLogger('nextcord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='nextcord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = nextcord.Intents.all()
bot_activity = nextcord.Activity(type=nextcord.ActivityType.listening, name="фонк")
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="/", intents=intents, status=nextcord.Status.idle, activity=bot_activity)

bot.add_cog(MusicCog(bot=bot))
bot.add_cog(ErrorCog(bot=bot))
bot.add_cog(UserCog(bot=bot))

@bot.event
async def on_ready():
    print("BOT ONLINE!")

bot.run(config.TOKEN)
