import json
import asyncio
import logging
import server2 as server
from typing import TYPE_CHECKING
from dotenv import dotenv_values
import asqlite
import twitchio
from twitchio import eventsub
from nicowiredbot import NicoWiredBot


if TYPE_CHECKING:
    import sqlite3


# setup global logging
file_handler = logging.FileHandler('nwbot.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
LOGGER: logging.Logger = logging.getLogger("Bot")
LOGGER.addHandler(file_handler)

# setup env vars
env_vars: dict = dotenv_values(".env")
CLIENT_ID: str = env_vars["CLIENT_ID"]
CLIENT_SECRET: str = env_vars["CLIENT_SECRET"]
BOT_ID = env_vars["BOT_ID"]
OWNER_ID = env_vars["OWNER_ID"]


async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist
    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == BOT_ID:
                continue

            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=BOT_ID)])

    return tokens, subs


def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO, handler=file_handler)

    # Prevent LOGGER from propagating to avoid duplicate logs
    LOGGER.propagate = False

    # Replace StreamHandlers with file_handler
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
            root_logger.addHandler(file_handler)

    # get social links
    with open("socials.json", "r") as f:
        socials = json.load(f)

    async def runner() -> None:
        # Start the server in a separate thread
        server.start()
        
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)

            async with NicoWiredBot(
                    token_database=tdb,
                    subs=subs,
                    config=dotenv_values(".env"),
                    logger=LOGGER,
                    socials=socials
                ) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)

                await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")


if __name__ == "__main__":
    main()
