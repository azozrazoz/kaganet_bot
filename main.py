import nextcord
from nextcord.ext import commands

import json

main_data = []

with open("data.json", 'r', encoding='UTF-8') as file:
    main_data = json.load(file)

# print(main_data)

intents = nextcord.Intents.all()
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot("$", intents=intents)


@bot.event
async def on_ready():
    print("BOT ONLINE!")


@bot.event  
async def on_member_join(member: nextcord.member.Member):
    channel = bot.get_channel(main_data[0]['join'])

    await channel.send(embed=nextcord.Embed(title=f"{member.name} итак, здравствуй!", color=0xffffff))


@bot.event
async def on_message(ctx):
    print(ctx)
    if ctx.channel.id == 1001425551434715156:
        member = ctx.author
        role = nextcord.utils.get(member.guild.roles, id=main_data[0]['id_role_new_member'])

        await member.add_roles(role)


@bot.event
async def on_raw_reaction_add(payload):
    # print(payload)
    # channel = bot.get_channel(1035189687427534848)
    # messages = await channel.history(limit=100).flatten()
    message_id = payload.message_id
    
    if message_id == 1041687082713763890: 
        for role_name in main_data[1]:
            if payload.emoji.name == role_name:
                role = nextcord.utils.get(payload.member.guild.roles, id=main_data[1][role_name])
                await payload.member.add_roles(role)
                break


@bot.event
async def on_raw_reaction_remove(payload):
    messageid = payload.message_id
    if messageid == 1041687082713763890: 
        for role_name in main_data[1]:
            if payload.emoji.name == role_name: 
                member = nextcord.utils.get(bot.get_all_members(), id=payload.user_id)
                role = nextcord.utils.get(member.guild.roles, id=main_data[1][role_name])
                await member.remove_roles(role)
                break



bot.run("")
