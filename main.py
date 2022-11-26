import nextcord
from nextcord.ext import commands
import requests
import json
from music_cog import MusicCog

intents = nextcord.Intents.all()
bot_activity = nextcord.Activity(type=nextcord.ActivityType.listening, name="фонк")
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="$", intents=intents, status=nextcord.Status.idle, activity=bot_activity)

bot.add_cog(MusicCog(bot=bot))


@bot.slash_command()
async def test(interaction):
    await interaction.send("Hello")


@bot.command(name="kurs")
async def kurs(ctx):
    data = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()

    await ctx.send(embed=nextcord.Embed(title="Курс на сегодня:", color=0xffffff, description=data['Date'])
    .add_field(name=data['Valute']['KZT']["Name"], value=data['Valute']['KZT']["Value"])
    .add_field(name=data['Valute']['USD']["Name"], value=data['Valute']['USD']["Value"])
    .add_field(name=data['Valute']['EUR']["Name"], value=data['Valute']['EUR']["Value"]))


@bot.event
async def on_ready():
    print("BOT ONLINE!")


bot.run("MTA0MTYxNDI0MTM2ODY0OTc3OA.GOxaB1.xc8k_apQVLOMp3AB62Ee3Z-Ju8MzG1jW08vRaw")
