import discord
from discord.ext import commands

import json

main_data = []

with open("data.json", 'r', encoding='UTF-8') as file:
    main_data = json.load(file)

print(main_data)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot("$", intents=intents)

@bot.event
async def on_ready():
    print("BOT ONLINE!")


@bot.event
async def on_member_join(member: discord.member.Member):
    channel = bot.get_channel(main_data[0]['join'])

    role = discord.utils.get(member.guild.roles, id=main_data[0]['id_roles'])

    await member.add_roles(role)
    await channel.send(embed=discord.Embed(title=f"{member.name} итак здравствуй!", color=0xffffff))


bot.run("MTA0MTYxNDI0MTM2ODY0OTc3OA.G-HRur.bUb6RxQA4NRuUZDoU0CMge0EappDo-J2VHVGI0")
