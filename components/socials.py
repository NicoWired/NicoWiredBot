from twitchio.ext import commands


class SocialsComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot):
        super().__init__()
        self.bot:commands.AutoBot = bot

    @commands.command(aliases=["linktree", "lt"])
    async def socials(self, ctx: commands.Context) -> None:
        ltree = self.bot.socials.get("linktree")
        if ltree:
            await ctx.send(f"Lintree with all of Nico's socials: {self.bot.socials["linktree"]}")

    @commands.command()
    async def discord(self, ctx: commands.Context) -> None:
        dc = self.bot.socials.get("discord")
        if dc:
            await ctx.send(f"Join us on Discord! {self.bot.socials["discord"]}")

    @commands.command(aliases=["x"])
    async def twitter(self, ctx: commands.Context) -> None:
        twitter = self.bot.socials.get("twitter")
        if twitter:
            await ctx.send(f"Follow Nico on Twitter {self.bot.socials["twitter"]}")

    @commands.command(aliases=["bsky"])
    async def bluesky(self, ctx: commands.Context) -> None:
        bsky = self.bot.socials.get("bluesky")
        if bsky:
            await ctx.send(f"Follow Nico on BlueSky {self.bot.socials["bluesky"]}")

    @commands.command(aliases=["gh"])
    async def github(self, ctx: commands.Context) -> None:
        github = self.bot.socials.get("github")
        if github:
            await ctx.send(f"Find Nico's code, including this bot, here: {self.bot.socials["github"]}")
    
    @commands.command(aliases=["help"])
    async def commands(self, ctx: commands.Context) -> None:
        await ctx.send(f"You can find all available commands here: https://tinyurl.com/5n6z53jx")