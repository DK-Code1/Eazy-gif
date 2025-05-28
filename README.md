# Eazy-gif
Eazy-gif is my attempt to recreate Ezgif into a standalone software so we can create and modify GIFS files entirely within our systems.
It is a multi platform software to convert video files into gifs files

#

![Guide image](https://github.com/DK-Code1/Eazy-gif/blob/main/guide.gif)
-----
![Sample gif](https://github.com/DK-Code1/Eazy-gif/blob/main/sample.gif)
#

# Features
- Multi-platform support (Windows and linux [arch, ubuntu] tested, OSX untested)
- Create GIFs.
- Ability to crop videos or gifs (Click and drag).
- Quickly export videos into mp4, webm, mkv.
- Cut videos from time selection.
- Cut video without re-encode.

# Requirements
- MPV libraries.
- FFMPEG binaries.
- Releases already come with mpv and ffmpeg (For Windows users).
- Linux users only need to install MPV as it comes ffmpeg automatically.

# This app uses
- Tkinter with customtkinter for GUI.
- MPV for video playing and preview with mpv-python implementation.
- ffmpeg-python wrapper for ffmpeg, to convert process videos and gifs.
- Mediainfo (File info).
- Opencv2 (File info).

# TO-DO
- Progress tracking.
- Add more languages.
- Migrate UI to PyQT gui for better visuals.
- UI for gif optimizations.
- GIFs operations (Edit frames, delete frames, change size / speed, etc.).
- Drag and drop support (With PyQt maybe).
