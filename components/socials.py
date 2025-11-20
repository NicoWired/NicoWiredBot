from twitchio.ext import commands

from components.social_messages import build_social_message

SOCIAL_COMMANDS =[
    # function name, aliases (if any)
    ("socials", ["linktree", "lt"]),
    ("discord", []),
    ("twitter", ["x"]),
    ("bluesky", ["bsky"]),
    ("github", ["gh"]),
    ("spotify", ["playlist"]),
]


class SocialsComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot):
        super().__init__()
        self.bot = bot
        for name, aliases in SOCIAL_COMMANDS:
            self._register_social_command(name, aliases)

    def _register_social_command(self, key: str, aliases: list[str]) -> None:
        async def command_creator(ctx: commands.Context) -> None:
            message = build_social_message(key, self.bot.socials)
            if message:
                await ctx.send(message)

        command_creator.__name__ = key
        social_command = commands.command(name=key, aliases=aliases)
        setattr(self, key, social_command(command_creator))

    @commands.command(aliases=["help"])
    async def commands(self, ctx: commands.Context) -> None:
        await ctx.send(f"You can find all available commands here: https://tinyurl.com/5n6z53jx")
