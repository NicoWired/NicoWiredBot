import sys
import importlib
import twitchio
from twitchio.ext import commands

async def load_components(bot: commands.AutoBot) -> None:
    # list of components to reload
    PRD_COMPONENTS = {
        "components.tts":  "TTSComponent",
        "components.socials":  "SocialsComponent",
        "components.routines": "RoutinesComponent",
    }
    for k,v in PRD_COMPONENTS.items():

        # remove module if it exists
        if v in bot._components:
            await bot.remove_component(v)
            bot.logger.info(f"Removed component: {v}")

        # Reload the module
        if k in sys.modules:
            new_module = importlib.reload(sys.modules[k])
        else:
            new_module = importlib.import_module(k)
        module_class = getattr(new_module, v, None)
        await bot.add_component(module_class(bot))
        bot.logger.info(f"Reloaded module: {k}")


class CoreComponent(commands.Component):
    # contains only the necessary commands for the bot to run

    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    @commands.is_broadcaster()
    @commands.command(aliases=["rl"])
    async def reload(self, _ctx) -> None:
        await load_components(self.bot)


    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

