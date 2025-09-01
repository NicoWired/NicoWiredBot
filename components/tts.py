import numpy as np
from twitchio.ext import commands
from kokoro import KPipeline
from datetime import datetime
from server import send_audio_to_obs


class TTSComponent(commands.Component):
    TTS_CD: int = 60

    def __init__(self, bot: commands.AutoBot):
        # not used yet, should be useful for a queueing system.
        super().__init__()
        self.tts_queue: list = []
        self.tts_playing: bool = False
        self.cooldown: dict = {}
        self.bot:commands.AutoBot = bot

    def check_cooldown(self, user_id: int):
        if (user_id in self.cooldown) and ((datetime.now().timestamp() - self.cooldown["cd"]) < self.TTS_CD):
            self.bot.logger.info(f"user {user_id} tried to use TTS while on cooldown")
            return

    @commands.command()
    async def tts(self, ctx: commands.Context, *message: str) -> None:
        # check if the user is allowed to run the command
        follower =  await ctx.chatter.follow_info()
        broadcaster: bool = (ctx.chatter == ctx.broadcaster)
        if not broadcaster:
            self.check_cooldown(ctx.chatter.id)
        if follower is None and broadcaster is False:
            self.bot.logger.info(f"user {ctx.chatter.id} tried to use TTS while not following")
            await ctx.send(f"{ctx.chatter} you need to follow {ctx.broadcaster} if you want to use this comamnd.")
            return
        print(5)
        self.bot.logger.info(f"user {ctx.chatter.id} successfuly invoked TTSD")
        self.cooldown.update({"user": ctx.chatter.id, "cd": datetime.now().timestamp()})

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

        # Send to websocket instead of playing locally
        send_audio_to_obs(full_audio, 24000)