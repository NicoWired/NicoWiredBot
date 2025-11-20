import datetime
import random

from twitchio.ext import commands, routines

from components.social_messages import available_social_commands, build_social_message

class RoutinesComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    @routines.routine(delta=datetime.timedelta(minutes=45), wait_first=True)
    async def socials_routine(self) -> None:
        commands_pool = available_social_commands(self.bot.socials)
        if not commands_pool:
            self.bot.logger.info("No social links configured; skipping social routine.")
            return

        command = random.choice(commands_pool)
        message = build_social_message(command, self.bot.socials)
        if not message:
            self.bot.logger.info("Social routine skipped; no message built for %s", command)
            return

        owner = await self.bot.fetch_user(id=self.bot.owner_id)
        await owner.send_message(
            message,
            sender=self.bot.bot_id,
            token_for=self.bot.bot_id,
        )

    async def component_load(self) -> None:
        await self.socials_routine.start()
