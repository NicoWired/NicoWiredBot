import asqlite
import twitchio
import logging
from twitchio.ext import commands
from components.core import CoreComponent, load_components
from twitchio import eventsub

class NicoWiredBot(commands.AutoBot):
    def __init__(
            self
            ,*
            ,token_database: asqlite.Pool
            , subs: list[eventsub.SubscriptionPayload]
            , config: dict
            , logger: logging.Logger
            , prefix:str = "!"
            , socials:str = {}
        ) -> None:
        self.token_database = token_database
        self.config = config
        self.logger = logger
        self.prefix = prefix
        self.socials = socials

        super().__init__(
            client_id=self.config["CLIENT_ID"],
            client_secret=self.config["CLIENT_SECRET"],
            bot_id=self.config["BOT_ID"],
            owner_id=self.config["OWNER_ID"],
            prefix=self.prefix,
            subscriptions=subs,
            force_subscribe=True,
            ignore_own_messages=False,
        )

    async def setup_hook(self) -> None:
        # add the core component. that component will take care of laoding everything else.
        await self.add_component(CoreComponent(self))
        await load_components(self)

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        # A list of subscriptions we would like to make to the newly authorized channel...
        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            self.logger.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        self.logger.info("Added token to the database for user: %s", resp.user_id)
        return resp
    
    async def event_ready(self) -> None:
        self.logger.info("---------------Successfully logged in as: %s", self.bot_id)
        print("NicoWiredBot is up and running")