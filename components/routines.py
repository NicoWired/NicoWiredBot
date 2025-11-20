from twitchio.ext import commands, routines
import datetime

class RoutinesComponent(commands.Component):
    def __init__(self, bot: commands.AutoBot) -> None:
        self.bot = bot

    # Define your routines here as methods, decorated with @routines.routine
    @routines.routine(delta=datetime.timedelta(minutes=1))  # Example: Runs every 1 minute
    async def example_routine(self):
        # Your routine logic here
        self.bot.logger.info("Example routine running: Checking something...")
        # Example: Send a message to the chat
        channel = await self.bot.fetch_channel("your_channel_name")  # Replace with your actual Twitch channel name (e.g., the broadcaster's username)
        await channel.send("Routine check: Everything looks good!")

    # Add more routines as needed
    @routines.routine(delta=datetime.timedelta(hours=1), iterations=5)  # Example: Runs every hour, up to 5 times
    async def hourly_reminder(self):
        self.bot.logger.info("Hourly reminder routine running...")
        # Add your logic

    async def component_load(self) -> None:
        # Start the routines when the component loads
        await self.example_routine.start()
        await self.hourly_reminder.start()
