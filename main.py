import nextcord
from nextcord.ext import commands
import requests
import json
from music_cog import MusicCog

main_data = []

with open("data.json", 'r', encoding='UTF-8') as file:
    main_data = json.load(file)


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
async def keep_alive(ctx):
    data = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()

    await ctx.send(embed=nextcord.Embed(title="Курс на сегодня:", color=0xffffff, description=data['Date'])
    .add_field(name=data['Valute']['KZT']["Name"], value=data['Valute']['KZT']["Value"])
    .add_field(name=data['Valute']['USD']["Name"], value=data['Valute']['USD']["Value"])
    .add_field(name=data['Valute']['EUR']["Name"], value=data['Valute']['EUR']["Value"]))


@bot.event
async def on_ready():
    print("BOT ONLINE!")


@bot.event  
async def on_member_join(member: nextcord.member.Member):
    channel = bot.get_channel(main_data[0]['join'])

    await channel.send(embed=nextcord.Embed(title=f"{member.name} итак, здравствуй!", color=0xffffff))


@bot.listen('on_message')
async def on_message(ctx):
    if ctx.channel.id == 1035189687427534848:
        member = ctx.author
        role = nextcord.utils.get(member.guild.roles, id=main_data[0]['id_role_new_member'])

        await member.add_roles(role)


@bot.event
async def on_raw_reaction_add(payload):
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


bot.run("token")
