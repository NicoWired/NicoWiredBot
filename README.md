# NicoWiredBot

A Twitch chat bot with advanced text-to-speech (TTS) capabilities using the Kokoro TTS model and Misaki G2P engine.

## Features

- **Real-time TTS**: Convert Twitch chat messages to speech using the Kokoro TTS model
- **Follower Verification**: Restrict TTS usage to channel followers
- **Custom Commands**: Support for various chat commands including `!tts`, `!reload`, etc.
- **High-Quality Audio**: Uses Kokoro's 82M parameter model for natural-sounding speech
- **Grapheme-to-Phoneme**: Integrated Misaki engine for accurate pronunciation
- **Audio Playback**: Real-time audio output using sounddevice

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/NicoWired/NicoWiredBot.git
   cd NicoWiredBot
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv nwbot
   source nwbot/bin/activate  # On Windows: nwbot\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Install Kokoro TTS
   cd kokoro
   pip install .
   cd ..

   # Install Misaki G2P engine
   cd misaki
   pip install .
   cd ..

   # Install additional dependencies
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
   pip install transformers phonemizer-fork espeakng-loader sounddevice
   ```

4. **Configure the bot:**
   - Update configuration files with your Twitch credentials
   - Adjust audio settings in `components/tts.py` if needed

## Usage

### Running the Bot

```bash
python main.py
```

### Chat Commands

- `!tts <message>` - Convert text to speech (followers only)
- `!reload` - Reload bot configuration
- `!rl` - Alias for reload

### Example Usage

```
[nicowired] - user: !tts Hello world!
[nicowired] - bot: Processing TTS request...
```

## Project Structure

```
NicoWiredBot/
├── main.py                 # Main bot entry point
├── nicowiredbot.py         # Core bot logic
├── components/
│   ├── core.py            # Core bot functionality
│   └── tts.py             # Text-to-speech implementation
├── kokoro/                # Kokoro TTS library
├── misaki/                # Misaki G2P engine
├── nwbot/                 # Python virtual environment
├── tokens.db              # Database for tokens
├── nwbot.log              # Bot log file
└── README.md              # This file
```

## Dependencies

### Core Dependencies
- **Kokoro**: Open-weight TTS model with 82M parameters
- **Misaki**: G2P engine for accurate pronunciation
- **PyTorch**: Deep learning framework
- **Transformers**: Hugging Face transformers library
- **Sounddevice**: Audio playback library

### Optional Dependencies
- **spaCy**: Natural language processing (for English TTS)
- **phonemizer-fork**: Phoneme conversion
- **espeakng-loader**: eSpeak NG integration

## Configuration

### Environment Variables
- Set up your Twitch API credentials
- Configure audio output device
- Adjust TTS model parameters

### Audio Settings
- Default sample rate: 24000 Hz
- Audio format: 16-bit PCM
- Output device: System default

## Development

### Adding New Commands

1. Edit `components/core.py`
2. Add new command handlers in the message processing loop
3. Update command documentation

### TTS Customization

1. Modify `components/tts.py`
2. Adjust Kokoro model parameters
3. Customize pronunciation rules in Misaki

## Troubleshooting

### Common Issues

1. **Audio not playing**: Check sounddevice installation and audio device permissions
2. **TTS errors**: Ensure all dependencies are properly installed
3. **Follower check failing**: Verify Twitch API credentials

### Logs

Check `nwbot.log` for detailed error messages and debugging information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Kokoro**: Open-weight TTS model by hexgrad
- **Misaki**: G2P engine for TTS
- **Twitch API**: For chat integration
- **PyTorch**: Deep learning framework

## Support

For issues and questions:
- Open an issue on GitHub
- Check the logs for error details
- Ensure all dependencies are correctly installed
