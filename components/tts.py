import sounddevice as sd
import numpy as np
from twitchio.ext import commands
from kokoro import KPipeline


class TTSComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot):
        # not used yet, should be useful for a queueing system.
        super().__init__()
        self.tts_queue: list = []
        self.tts_playing: bool = False
        self.bot = bot
    
    @commands.command()
    async def tts(self, ctx: commands.Context, *message: str) -> None:
        # check if the user is allowed to run the command
        follower =  await ctx.chatter.follow_info()
        broadcaster: bool = (ctx.chatter == ctx.broadcaster)
        print(ctx.broadcaster)
        print(ctx.chatter)
        print(broadcaster)
        if follower is None and broadcaster is False:
            await ctx.send(f"{ctx.chatter} you need to follow {ctx.broadcaster} if you want to use this comamnd.")
            return

        pipeline = KPipeline(lang_code='a') # a = english
        text = ' '.join(message)

        # Collect all chunks into one array
        generator = pipeline(text, voice='af_heart')
        all_audio = []
        for i, (gs, ps, audio) in enumerate(generator):
            print(i, gs, ps)
            all_audio.append(audio)

        # Concatenate into one continuous waveform
        full_audio = np.concatenate(all_audio)

        # Increase volume (multiply by 2.0 for 2x louder, adjust as needed)
        volume_factor = 2.0
        full_audio = full_audio * volume_factor

        # Prevent clipping by ensuring values stay within [-1, 1]
        full_audio = np.clip(full_audio, -1.0, 1.0)

        # Play once
        sd.play(full_audio, 24000)
        sd.wait()

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        if ctx.chatter == ctx.broadcaster:
            sd.stop()