import numpy as np
from twitchio.ext import commands
from kokoro import KPipeline
from datetime import datetime
from server2 import send_audio_to_obs


class TTSComponent(commands.Component):
    TTS_CD: int = 60

    def __init__(self, bot: commands.AutoBot):
        super().__init__()
        #self.tts_queue: list = []
        #self.tts_playing: bool = False
        self.cooldown: dict = {}
        self.bot:commands.AutoBot = bot

    def check_cooldown(self, user_id: int) -> bool:
        if (user_id in self.cooldown) and ((datetime.now().timestamp() - self.cooldown["cd"]) < self.TTS_CD):
            self.bot.logger.info(f"user {user_id} tried to use TTS while on cooldown")
            return True
        return False

    @commands.command()
    async def tts(self, ctx: commands.Context, *message) -> None:
        # check if the user is allowed to run the command
        follower =  await ctx.chatter.follow_info()
        broadcaster: bool = (ctx.chatter == ctx.broadcaster)
        if not broadcaster:
            if self.check_cooldown(ctx.chatter.id):
                return
        if follower is None and broadcaster is False:
            self.bot.logger.info(f"user {ctx.chatter.id} tried to use TTS while not following")
            await ctx.send(f"{ctx.chatter} you need to follow {ctx.broadcaster} if you want to use this comamnd.")
            return
        
        # cleanup message
        text = ' '.join(message)
        if len(text) == 0:
            ctx.send(f"""@{ctx.chatter} you need to specify a message for the TTS.
                     Example: "!tts this is the best stream ever!" """)
            return
        text = text.replace("'", "")
        text = text.replace('"', '')

        self.bot.logger.info(f"user {ctx.chatter.id} successfuly invoked TTSD")
        self.cooldown.update({"user": ctx.chatter.id, "cd": datetime.now().timestamp()})

        pipeline = KPipeline(lang_code='a') # a = english

        # Collect all chunks into one array
        generator = pipeline(text, voice='af_heart')
        all_audio = []
        for i, (gs, ps, audio) in enumerate(generator):
            print(i, gs, ps)
            all_audio.append(audio)
        full_audio = np.concatenate(all_audio)

        send_audio_to_obs(full_audio, 24000)
        