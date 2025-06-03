# Video Library Application

A desktop application for browsing and watching videos from folders on your local machine.

## Features

- **Folder Browsing**: Navigate through your computer's folders and select video directories.
- **Video Playback**: Built-in video player with standard controls.
- **Thumbnail Grid**: View videos as thumbnails in a grid layout.
- **Video Preview**: Hover over videos to see a preview and information.
- **Tagging**: Add custom tags to videos for better organization.
- **Watched Status**: Track which videos you've already watched.
- **Notes & Reviews**: Add personal notes for each video.
- **Search & Filter**: Find videos by name, tags, or watch status.
- **Light & Dark Themes**: Switch between two visual themes.
- **File Management**: Rename and delete videos directly from the app.

## Installation

### Requirements

- Windows OS
- Python 3.8 or higher (if running from source)

### Running the Executable

1. Download the latest release from the releases page.
2. Extract the zip file.
3. Run `VideoLibrary.exe`.

### Running from Source

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/VideoLibraryApp.git
   cd VideoLibraryApp
   ```

2. Install requirements:

   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

## Building from Source

To build the executable from source:

1. Make sure all requirements are installed:

   ```
   pip install -r requirements.txt
   ```

2. Run the build script:

   ```
   python build.py
   ```

3. The executable will be created in the `dist` directory.

## Usage

### Getting Started

1. Open the application.
2. Use the folder browser on the left to navigate to a directory containing videos.
3. Click on a folder to load all videos in that folder.
4. Double-click on a video to play it in the built-in player.

### Keyboard Shortcuts

- **Space**: Play/Pause video
- **F**: Toggle fullscreen
- **S**: Stop video
- **←/→**: Seek backward/forward
- **↑/↓**: Increase/decrease volume
- **T**: Toggle between light and dark themes
- **F5**: Refresh current folder
- **Delete**: Delete selected video(s)
- **F2**: Rename selected video

### Video Management

- Right-click on videos for options (play, mark as watched, rename, delete, etc.)
- Use the search bar to filter videos by name
- Use the filters to sort by different criteria or filter by tags/watched status

## Project Structure

- `app.py`: Main application entry point
- `main.py`: Core application logic
- `ui/`: User interface modules
- `utils/`: Utility functions and helper classes
- `db/`: Database handling
- `resources/`: Application resources (icons, styles)

## Dependencies

- PyQt5: GUI framework
- OpenCV: Video processing and thumbnail extraction
- SQLite: Local database storage
- QDarkStyle: Dark theme styling

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## For Video Playback Issues

If you experience problems with video playback (videos not opening or playing), please install the K-Lite Codec Pack:

1. Download K-Lite Codec Pack Standard from the official website: https://codecguide.com/download_k-lite_codec_pack_standard.htm
2. Run the installer and follow the installation instructions
3. Choose the "Normal" installation mode for most users
4. Once installed, restart the Video Library application

The K-Lite Codec Pack provides the necessary video codecs for Windows to properly decode and play various video formats.

## Building Executable

To build a standalone executable:

```
python build.py
```

This will generate a VideoLibrary.exe file in the dist folder.
