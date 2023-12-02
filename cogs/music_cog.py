import nextcord
from nextcord import Interaction
from nextcord.ext import commands
import asyncio
import functools
import random
import yt_dlp as youtube_dl

from cogs.messages import MESSAGES_RU, MESSAGES_KZ, MESSAGES_EN, EMOJIS_IN_MESSAGES


class YTDLError(Exception):
    pass


# Работа с ютубом и поиск песни в нем
class YTDLSource(nextcord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'force-ipv4': True,
        'cachedir': False
    }

    FFMPEG_OPTIONS = {
        'before_options':
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self,
                 interaction: Interaction,
                 source: nextcord.FFmpegPCMAudio,
                 *,
                 data: dict,
                 volume: float = 1.0):
        super().__init__(source, volume)

        self.requester = interaction.user
        self.channel = interaction.user.voice.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(
                'Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(
                    'Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop()
                except IndexError:
                    raise YTDLError(
                        'Couldn\'t retrieve any matches for `{}`'.format(
                            webpage_url))

        return info

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append(f'{days} days')
        if hours > 0:
            duration.append(f'{hours} hours')
        if minutes > 0:
            duration.append(f'{minutes} minutes')
        if seconds > 0:
            duration.append(f'{seconds} seconds')

        return ', '.join(duration)
    

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.is_paused = False
        self.is_playing = False
        self.loop = False

        self.queue = []
        
        self.current = None
        self.current_embed = None

        self.voice_channel = None

        self.requester = None
        self.color_embed = 0xffffff
        self.message = MESSAGES_RU
        self.lang_select = "RU"

        self.YDL_OPTIONS = {'format': 'bestaudio/best', 'extractaudio': True,
                            'audioformat': 'mp3',
                            'outtmpl': u'%(id)s.%(ext)s',
                            'noplaylist': True,
                            'nocheckcertificate': True,
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }]}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        
        
    def change_lang(self):
        if self.lang_select == "KZ":
            self.message = MESSAGES_RU
            self.lang_select = "RU"
        elif self.lang_select == "RU":
            self.message = MESSAGES_EN
            self.lang_select = "EN"
        else:
            self.message = MESSAGES_KZ
            self.lang_select = "KZ"
            
        return self.lang_select
        

    def create_embed(self):
        embed = (nextcord.Embed(title='Сейчас играет', 
                                description=f"```css\n{self.queue[0][0]['title']}\n```", 
                                color=self.color_embed)
                                .add_field(name='Время', value=YTDLSource.parse_duration(self.queue[0][0]['duration']))
                                .add_field(name='Запрос от', value=self.requester.mention)
                                .add_field(name='Загружено с', value=f"[{self.queue[0][0]['uploader']}]({self.queue[0][0]['uploader_url']})")                 
                                .add_field(name='SOURCE', value=f"[Click]({self.queue[0][0]['url']})")
                                .add_field(name='URL', value=f"[Click]({self.queue[0][0]['webpage_url']})")
                                .add_field(name='VIEWS', value=f"{self.queue[0][0]['view_count']}")
                                .set_thumbnail(url=self.queue[0][0]['thumbnail'])
                                )

        return embed
    
    
    @nextcord.slash_command(name="language")
    async def language(self, interaction: nextcord.Interaction):
        await interaction.send(f"Language switch on {self.change_lang()}")

    @nextcord.slash_command(name='play')
    async def _play(self, interaction: Interaction, search: str = None):
        if search is None:
            await interaction.send(self.message['HOW_TO_PLAY'])
            return

        try:
            channel = interaction.user.voice.channel
        except AttributeError:
            await interaction.send(f"{interaction.user.mention}  {self.message['user_voice_channel_is_empty']}")
            return

        if self.voice_channel is None:
            await self._join(interaction)

        if not channel == self.voice_channel:
            await self._summon(interaction.user)

        await interaction.response.defer()
        song = await YTDLSource.create_source(search)

        if not song:
            await interaction.send(self.message['ERROR'])
            return
    
        self.queue.append([song, interaction.user.voice.channel])
        
        await interaction.followup.send(f"{self.message['add_song']} **{song['title']}**")

        self.requester = interaction.user

        if not self.is_playing:
            self.current_embed = self.create_embed()
            await interaction.send(embed=self.current_embed)
            self._play_next()

    @nextcord.slash_command(name='playlist')
    async def _playlist(self, interaction: Interaction, *, search=None):
        if search is None:
            await interaction.send(self.message['HOW_TO_PLAY_PLAYLIST'])
            return

        try:
            channel = interaction.message.user.voice.channel
        except AttributeError:
            await interaction.send(f"{interaction.user.mention} {self.message['user_voice_channel_is_empty']}")
            return

        if self.voice_channel is None:
            await self._join(interaction)

        elif not channel == self.voice_channel:
            await self._summon(interaction.message.user.voice.channel)

        await interaction.response.defer()

        for one_song in str.split(search, ';'):
            song = await YTDLSource.create_source(one_song)

            if not song:  
                await interaction.send(self.message['ERROR'])
                return

            self.queue.append([song, interaction.user.voice.channel])

            await interaction.followup.send(f"{self.message['add_song']} {song['title']}")
            self.requester = interaction.user

            if not self.is_playing:
                self.current_embed = self.create_embed()
                await interaction.send(embed=self.current_embed, )
                self._play_next()

    def _play_next(self):
        self.voice_channel.stop()

        if self.loop:
            self.voice_channel.play(nextcord.FFmpegPCMAudio(self.current, **self.FFMPEG_OPTIONS), after=lambda e: self._play_next())
        elif len(self.queue) > 0:
            self.is_playing = True

            url = self.queue[0][0]['url']

            self.voice_channel.play(nextcord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS), after=lambda e: self._play_next())

            self.current = url
            self.current_embed = self.create_embed()
            self.queue.pop(0)

        else:
            self.is_playing = False
            self.current = None
            self.current_embed = None

    @nextcord.slash_command(name='stop')
    async def _stop(self, interaction: Interaction):
        if self.requester is interaction.user:
            self.queue.clear()

            if self.is_playing:
                self.voice_channel.stop()
                self.loop = False
                await interaction.send(f"{interaction.user.mention} {EMOJIS_IN_MESSAGES['stop']} {self.message['is_not_stop']}")

            await self._leave(interaction)
        else:
            await interaction.send(f"{EMOJIS_IN_MESSAGES['stop']} {self.message['is_stop']}")

    @nextcord.slash_command(name='pause')
    async def _pause(self, interaction: Interaction):
        if self.is_playing:
            self.voice_channel.pause()
            self.is_playing = False
            self.is_paused = True
            await interaction.send(f"{interaction.user.mention} {EMOJIS_IN_MESSAGES['pause']} {self.message['is_not_pause']}")
        else:
            await interaction.send(f"{interaction.user.mention} {EMOJIS_IN_MESSAGES['pause']} {self.message['is_pause']}")


    @nextcord.slash_command(name='resume')
    async def _resume(self, interaction: Interaction):
        if not self.is_playing and self.is_paused:
            self.voice_channel.resume()
            self.is_playing = True
            self.is_paused = False
            await interaction.send(f"{interaction.user.mention} {EMOJIS_IN_MESSAGES['resume']} {self.message['is_not_resume']}")
        else:
            await interaction.send(f"{interaction.user.mention} {EMOJIS_IN_MESSAGES['resume']} {self.message['is_resume']}")


    @nextcord.slash_command(name='skip')
    async def _skip(self, interaction: Interaction):
        if not self.voice_channel.is_playing:
            return await interaction.send(self.message['nothing_is_playing'])
        if len(self.queue) > 0:
            await interaction.send(f"{interaction.user.mention} {self.message['skip']}")

            self.voice_channel.stop()
            await self.cog_after_invoke(interaction)
            return
        else:
            self.voice_channel.stop()

    @nextcord.slash_command(name='now')
    async def _now(self, interaction: Interaction):
        if self.is_playing:
            return await interaction.send(embed=self.current_embed)
        else:
            return await interaction.send(self.message['nothing_is_playing'])

    @nextcord.slash_command(name='loop')
    async def _loop(self, interaction: Interaction):
        if not self.is_playing:
            return await interaction.send(self.message['nothing_is_playing'])

        self.loop = not self.loop
        if self.loop:
            await interaction.send(f"{EMOJIS_IN_MESSAGES['loop']} {self.message['is_not_loop']}")
        else:
            await interaction.send(f"{EMOJIS_IN_MESSAGES['loop']} {self.message['is_loop']}")

    @nextcord.slash_command(name='queue')
    async def _queue(self, interaction: Interaction):
        if len(self.queue) <= 0:
            await interaction.send(self.message['queue_is_empy'])
            return

        retval = ""
        for i in range(0, len(self.queue)):
            if i > 4:
                break
            retval += '```css' + self.queue[i][0]['title'] + "```\n"

        await interaction.send(embed=nextcord.Embed(description=retval, color=0xcfbdf4))

    @nextcord.slash_command(name='shuffle')
    async def _shuffle(self, interaction: Interaction):
        if len(self.queue) == 0:
            return await interaction.send(self.message['queue_is_empy'])

        random.shuffle(self.queue)
        await interaction.send(self.message['shuffle'])

    @nextcord.slash_command(name='clear')
    async def _clear(self, interaction):
        self.queue.clear()
        await interaction.send(f"{EMOJIS_IN_MESSAGES['clear']} {self.message['clear']}")

    # Function for join to channel
    async def _join(self, interaction: Interaction):
        self.voice_channel = await interaction.user.voice.channel.connect()

    # Function for leave from channel
    async def _leave(self, interaction: Interaction):
        if not self.voice_channel:
            return await interaction.send(f"{interaction.user.mention} {self.message['voice_channel_is_empty']}")

        self.voice_channel.stop()
        await interaction.send(f"{self.message['leave_from_channel']} ```{str(interaction.user.voice.channel)}```")
        await self.voice_channel.disconnect()
        self.voice_channel = None
        self.is_playing = False
        self.current = None
        self.requester = None
        self.is_paused = False
        self.loop = False
        self.current_embed = None

    async def _summon(self, user):
        await self.voice_channel.move_to(user)
