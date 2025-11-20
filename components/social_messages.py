from __future__ import annotations

from typing import Mapping


# Command names to the key used in the socials dictionary.
_SOCIAL_KEYS: dict[str, str] = {
    "socials": "linktree",
    "discord": "discord",
    "twitter": "twitter",
    "bluesky": "bluesky",
    "github": "github",
    "spotify": "spotify",
}


def build_social_message(command: str, socials: Mapping[str, str]) -> str | None:
    """Return the chat message for a social command or None if data is missing."""
    key = _SOCIAL_KEYS.get(command)
    if not key:
        return None

    url = socials.get(key)
    if not url:
        return None

    templates: dict[str, str] = {
        "socials": "Linktree with all of Nico's socials: {url}",
        "discord": "Join us on Discord! {url}",
        "twitter": "Follow Nico on Twitter {url}",
        "bluesky": "Follow Nico on BlueSky {url}",
        "github": "Find Nico's code, including this bot, here: {url}",
        "spotify": "Nico's playlist: {url}",
    }

    template = templates.get(command)
    if not template:
        return None

    return template.format(url=url)


def available_social_commands(socials: Mapping[str, str]) -> list[str]:
    """Commands that have data available, excluding the help/commands entry."""
    return [command for command in _SOCIAL_KEYS.keys() if build_social_message(command, socials)]
