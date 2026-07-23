# Speech-to-Text Transcription Tool

A desktop application for transcribing speech to text — supports both
transcribing existing audio files and live microphone transcription, with
a styled GUI and a command-line interface.

## Features

- **File transcription** — convert audio files (e.g. `.wav`, `.mp3`) into text
- **Live microphone transcription** — transcribe speech in real time as you speak
- **Desktop GUI** — built with Tkinter/ttk for a simple, styled interface
- **CLI wrapper** — run transcription from the command line for scripting/automation

## Project structure

```
speech-to-text/
├── transcribe.py       # Core transcription logic (file + live mic)
├── gui.py              # Tkinter desktop GUI
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.9+
- A working microphone (for live transcription)
- `ffmpeg` installed on your system (required by `pydub` for audio file handling)
  - macOS: `brew install ffmpeg`
  - Windows: download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
  - Linux: `sudo apt install ffmpeg`

## Setup

```bash
git clone https://github.com/zaynsblessings777/speech-to-text.git
cd speech-to-text
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### GUI
```bash
python3 gui.py
```
Opens the desktop app — choose an audio file to transcribe, or start live
microphone transcription from the interface.

### Command line
```bash
python3 transcribe.py --file path/to/audio.wav
```
or for live microphone transcription:
```bash
python3 transcribe.py --live
```

> **Note:** confirm the exact CLI flags/arguments against `transcribe.py`'s
> `argparse` setup — update this section if your actual flag names differ
> from `--file` / `--live`.

## Built with

- `speech_recognition` — speech-to-text engine
- `pydub` — audio file handling
- `tkinter` / `ttk` — desktop GUI
- `argparse` — CLI argument parsing
- `threading` — keeps the GUI responsive during live transcription

## Notes

Transcription accuracy depends on audio quality, background noise, and
microphone input level. For best results with live transcription, use a
quiet environment and a decent microphone.
