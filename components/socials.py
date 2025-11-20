from twitchio.ext import commands

from components.social_messages import build_social_message


class SocialsComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot):
        super().__init__()
        self.bot: commands.AutoBot = bot

    @commands.command(aliases=["linktree", "lt"])
    async def socials(self, ctx: commands.Context) -> None:
        message = build_social_message("socials", self.bot.socials)
        if message:
            await ctx.send(message)

    @commands.command()
    async def discord(self, ctx: commands.Context) -> None:
        message = build_social_message("discord", self.bot.socials)
        if message:
            await ctx.send(message)

    @commands.command(aliases=["x"])
    async def twitter(self, ctx: commands.Context) -> None:
        message = build_social_message("twitter", self.bot.socials)
        if message:
            await ctx.send(message)

    @commands.command(aliases=["bsky"])
    async def bluesky(self, ctx: commands.Context) -> None:
        message = build_social_message("bluesky", self.bot.socials)
        if message:
            await ctx.send(message)

    @commands.command(aliases=["gh"])
    async def github(self, ctx: commands.Context) -> None:
        message = build_social_message("github", self.bot.socials)
        if message:
            await ctx.send(message)

    @commands.command(aliases=["playlist"])
    async def spotify(self, ctx: commands.Context) -> None:
        message = build_social_message("spotify", self.bot.socials)
        if message:
            await ctx.send(message)
    
    @commands.command(aliases=["help"])
    async def commands(self, ctx: commands.Context) -> None:
        await ctx.send(f"You can find all available commands here: https://tinyurl.com/5n6z53jx")
