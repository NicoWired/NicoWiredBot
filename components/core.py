import sys
import importlib
import twitchio
from twitchio.ext import commands


class CoreComponent(commands.Component):
    # contains only the necessary commands for the bot to run

    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    @commands.command(aliases=["rl"])
    async def reload(self, _ctx) -> None:

        # list of components to reload
        PRD_COMPONENTS = {
            "components.tts":  "TTSComponent",
        }
        for k,v in PRD_COMPONENTS.items():

            # remove module if it exists
            if v in self.bot._components:
                await self.bot.remove_component(v)
                self.bot.logger.info(f"Removed component: {v}")

            # Reload the module
            if k in sys.modules:
                new_module = importlib.reload(sys.modules[k])
            else:
                new_module = importlib.import_module(k)
            module_class = getattr(new_module, v, None)
            await self.bot.add_component(module_class(self.bot))
            self.bot.logger.info(f"Reloaded module: {k}")

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

