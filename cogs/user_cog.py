import nextcord
from nextcord.ext import commands
import requests


class UserCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @nextcord.slash_command(name="test")
    async def test(self, interaction: nextcord.Interaction):
        await interaction.send("Hello, I'm test command :)")


    @nextcord.slash_command(name="forex")
    async def kurs(self, interaction: nextcord.Interaction):
        data = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()

        await interaction.send(embed=nextcord.Embed(title="Курс на сегодня:", color=0xffffff, description=data['Date'])
        .add_field(name=data['Valute']['KZT']["Name"], value=data['Valute']['KZT']["Value"])
        .add_field(name=data['Valute']['USD']["Name"], value=data['Valute']['USD']["Value"])
        .add_field(name=data['Valute']['EUR']["Name"], value=data['Valute']['EUR']["Value"]))

