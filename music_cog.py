import asyncio
import functools
import random
import nextcord
from nextcord.ext import commands
import youtube_dl


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
                 ctx: commands.Context,
                 source: nextcord.FFmpegPCMAudio,
                 *,
                 data: dict,
                 volume: float = 1.0):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
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
    async def create_source(cls,
                            search: str,
                            *,
                            loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info,
                                    search,
                                    download=False,
                                    process=False)
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
        partial = functools.partial(cls.ytdl.extract_info,
                                    webpage_url,
                                    download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
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
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.is_paused = False
        self.bot = bot
        self.is_playing = False
        self.loop = False

        self.queue = []
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
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                               'options': '-vn'}
        self.current = None
        self.current_embed = None

        self.voice_channel = None

        self.requester = None
        self.color_embed = 0xffffff

    def create_embed(self):
        embed = (nextcord.Embed(
            title='Сейчас играет',
            description=f"```css\n{self.queue[0][0]['title']}\n```",
            color=self.color_embed)
                 .add_field(name='Время', value=YTDLSource.parse_duration(self.queue[0][0]['duration']))
                 .add_field(name='Запрос от', value=self.requester.mention)
                 .add_field(name='Загружено с',
                            value=f"[{self.queue[0][0]['uploader']}]({self.queue[0][0]['uploader_url']})")
                 .add_field(name='SOURCE',
                            value=f"[Click]({self.queue[0][0]['url']})")
                 .add_field(name='URL',
                            value=f"[Click]({self.queue[0][0]['webpage_url']})")
                 .set_thumbnail(url=self.queue[0][0]['thumbnail'])
                 )

        return embed

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search=None):
        if search is None:
            await ctx.send("Нужно отправить ссылку на видео или его название")
            return

        try:
            channel = ctx.message.author.voice.channel
        except AttributeError:
            await ctx.send(f'{ctx.author.mention} чел тыы, сам не в гс :/')
            return

        if self.voice_channel is None:
            await self._join(ctx)

        elif not channel == self.voice_channel:
            await self._summon(ctx.message.author.voice.channel)

        async with ctx.typing():

            # song = self.search_yt(search)
            song = await YTDLSource.create_source(search)

            if not song:
                await ctx.send("Произошла ошибка")
                return

            self.queue.append([song, ctx.author.voice.channel])
            
            await ctx.send('Добавлено: **{}**'.format(str(song['title'])))
            self.requester = ctx.author

            if not self.is_playing:
                self.current_embed = self.create_embed()
                await ctx.send(embed=self.current_embed, )
                self._play_next()

    def _play_next(self):
        self.voice_channel.stop()

        if self.loop:
            self.voice_channel.play(nextcord.FFmpegPCMAudio(self.current,
                                                           **self.FFMPEG_OPTIONS),
                                    after=lambda e: self._play_next())
        elif len(self.queue) > 0:
            self.is_playing = True

            url = self.queue[0][0]['url']

            self.voice_channel.play(nextcord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS),
                                    after=lambda e: self._play_next())

            self.current = url
            self.current_embed = self.create_embed()
            self.queue.pop(0)

        else:
            self.is_playing = False
            self.current = None
            self.current_embed = None

    @commands.command(name='stop')
    async def _stop(self, ctx: commands.Context):
        if self.requester is ctx.author:
            self.queue.clear()
            await self._leave(ctx)

            if self.is_playing:
                self.voice_channel.stop()
                self.loop = False
                await ctx.message.add_reaction('⏹')
                await ctx.send(f"{ctx.author.mention} ваша полная остановочка!")

        else:
            await ctx.send("Не твой уровень дорогой :)")

    @commands.command(name='pause')
    async def _pause(self, ctx):
        if self.is_playing:
            self.voice_channel.pause()
            self.is_playing = False
            self.is_paused = True
            await ctx.send(f"{ctx.author.mention} ваша остановочка!")

    @commands.command(name='resume')
    async def _resume(self, ctx):
        if not self.is_playing and self.is_paused:
            self.voice_channel.resume()
            self.is_playing = True
            self.is_paused = False
            await ctx.send(f"{ctx.author.mention} поехали!")

    @commands.command(name='skip')
    async def _skip(self, ctx):
        if not self.voice_channel.is_playing:
            return await ctx.send('Пока что ничего не играет :|')
        if len(self.queue) > 0:
            await ctx.send(f'{ctx.author.mention} зачееем, ну ладно')

            self.voice_channel.stop()
            await self.cog_after_invoke(ctx)
            return
        else:
            self.voice_channel.stop()

    @commands.command(name='now')
    async def _now(self, ctx):
        if self.is_playing:
            return await ctx.send(embed=self.current_embed)
        else:
            return await ctx.send('Пока что ничего не играет :|')

    @commands.command(name='loop', aliases=['l'])
    async def _loop(self, ctx):
        if not self.is_playing:
            return await ctx.send('Пока что ничего не играет :|')

        self.loop = not self.loop
        if self.loop:
            await ctx.message.add_reaction('✅')
            await ctx.send('Будет сделано!')
        else:
            await ctx.message.add_reaction('✅')
            await ctx.send('Будет сделано, но в другую сторону')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx):
        if len(self.queue) <= 0:
            await ctx.send("бак пуст :(")
            return

        retval = ""
        for i in range(0, len(self.queue)):
            if i > 4:
                break
            retval += '**' + self.queue[i][0]['title'] + "**\n"

        await ctx.send(embed=nextcord.Embed(description=retval, color=0xcfbdf4))

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx):
        if len(self.queue) == 0:
            return await ctx.send('Бак пуст, плз залей 92 :)')

        random.shuffle(self.queue)
        await ctx.message.add_reaction('✅')

    @commands.command(name='clear')
    async def _clear(self, ctx):
        self.queue.clear()
        await ctx.send("Бак очищен, но все равно залей 92")

    async def _join(self, ctx):
        self.voice_channel = await ctx.author.voice.channel.connect()

    async def _leave(self, ctx):
        if not self.voice_channel:
            return await ctx.send(f"{ctx.author.mention} ты думал я в гс? а нееет")

        self.voice_channel.stop()
        await ctx.send(f"я пошел, бывайте :3 {str(ctx.author.voice.channel)[1:]}")
        await self.voice_channel.disconnect()
        self.voice_channel = None
        self.is_playing = False
        self.current = None
        self.requester = None
        self.is_paused = False
        self.loop = False
        self.current_embed = None

    async def _summon(self, author):
        await self.voice_channel.move_to(author)
