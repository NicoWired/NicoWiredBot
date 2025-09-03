## NicoWiredBot — Commands Reference

This file lists the available bot chat commands (Twitch).
---

## Twitch Chat Commands
- `!tts <message>`
  - Description: Text-to-speech command.
  - Permission/Requirements:
    - Nust be following the channel.
    - Cooldown: 60 seconds.
  - Usage examples:
    - `!tts Hello everyone, Nico is the best streamer ever!`

- `!socials` (aliases: `!linktree`, `!lt`)
  - Description: Posts the Linktree link.
  - Usage: `!socials`

- `!discord`
  - Description: Posts the Discord invite.
  - Usage: `!discord`

- `!twitter` (alias: `!x`)
  - Description: Posts the Twitter profile link.
  - Usage: `!twitter` or `!x`

- `!bluesky` (alias: `!bsky`)
  - Description: Posts the BlueSky profile link.
  - Usage: `!bluesky` or `!bsky`

- `!github` (alias: `!gh`)
  - Description: Posts the GitHub profile.
  - Usage: `!github` or `!gh`

- `!commands` (alias: `!help`)
  - Description: Posts a link to this page.
  - Usage: `!commands` or `!help`

---

## HTTP / Web Server Endpoints

The repository provides a small aiohttp-based server (see `server.py`) which exposes endpoints used for the OBS/web UI and tests. These are primarily for the TTS / audio bridge and developer testing.

- `GET /` (root)
  - Description: Serves a small HTML page (web client) that connects to the SSE endpoint and plays incoming WAV audio messages in the browser. Useful for testing audio delivery.

- `GET /events` (SSE)
  - Description: Server-Sent Events endpoint. The web client connects here and receives JSON events with audio payloads.
  - Event types: `audio` (base64-encoded WAV), `ping` (heartbeat).

- `GET /test-tone`
  - Description: Queues a short test tone to all connected SSE clients (non-blocking). Used to verify audio path.
  - Response: JSON `{"status": "queued"}`.
  - Usage example (developer): Use the web UI root page and click "Server Test Tone" or request this endpoint.

- `GET /inject?text=<text>`
  - Description: Queues a synthetic beep-like audio clip derived from the `text` query parameter (debug helper).
  - Response: JSON `{"status": "queued", "text": "<text>"}`.
  - Usage example: `/inject?text=hello%20world`

- `GET /ping`
  - Description: Health check endpoint. Returns `{"status": "ok"}`.

- `GET /ua?ua=<encoded user agent>`
  - Description: Logs the provided User-Agent string (used by the web client to report UA). Returns a 1x1 GIF pixel.

---

## Notes, Permissions and Edge Cases

- Config: Many commands read values from `socials.json` and `.env`. Ensure these files contain the expected keys (e.g., `linktree`, `discord`, `twitter`, `github`) for socials commands to work.
- TTS: Requires the TTS pipeline dependencies (`kokoro`, `numpy`, etc.) and the server running to actually route audio to the web client / OBS.
- Error handling: Some commands avoid sending anything if the expected config key is missing; you may want to add a fallback message for users.

---

## Suggested Improvements

- Fix `!commands` implementation to send a URL (for example, your repo's `commands.md` or README) so users can access the full command list in chat.
- Add explicit user feedback when social links are missing.
- Add a `!help tts` style command to show TTS usage & cooldown info in chat.

---

## File added

- `commands.md` — this file: list of available chat commands and server endpoints, with usage and notes.

## Status

- Requested: Create `commands.md` with full list of all commands available + descriptions and usage — Done.
