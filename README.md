# xgamma GUI Tool

Graphical tool for managing display gamma settings using the xgamma command on Linux systems.

## Description

xgamma GUI Tool provides a simple, minimalist interface for adjusting gamma correction for red, green, and blue channels individually or together. It allows you to preview changes in real-time and automatically apply saved settings on system startup.

## Requirements

- Linux Mint / Ubuntu (tested on Ubuntu 20.04 LTS, Ubuntu 22.04 LTS, Linux Mint 20.x, Linux Mint 21.x)
- Python 3.8 or higher
- xgamma (x11-xserver-utils package)
- PyQt5

## Installation

### 1. Install xgamma

**Ubuntu/Debian:**
```bash
sudo apt-get install x11-xserver-utils
```

**Fedora:**
```bash
sudo dnf install xorg-x11-server-utils
```

**Arch Linux:**
```bash
sudo pacman -S xorg-xgamma
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Or using pip3:
```bash
pip3 install -r requirements.txt
```

## Usage

### Running the application

From the project root directory:
```bash
python main.py
```

Or:
```bash
python3 main.py
```

### Features

- **Individual channel control**: Adjust red, green, and blue gamma values separately
- **Overall gamma control**: Adjust all channels simultaneously
- **Real-time preview**: See changes immediately on the reference test pattern
- **Autostart support**: Save settings to be applied automatically on system startup
- **Reset function**: Quickly reset all values to default (1.0) and remove autostart entries

### Interface

- **Reference image**: Test pattern with gradients and color blocks for visual calibration
- **Sliders**: Horizontal sliders for each color channel (Red, Green, Blue) and overall gamma (All)
- **Value inputs**: Numeric fields showing current slider values (editable)
- **Reset button**: Resets all values to 1.0 and removes autostart entries
- **Save to Autostart button**: Saves current settings to be applied on system startup

### Gamma Range

- Minimum: 0.01
- Maximum: 5.0
- Step: 0.01
- Default: 1.0 for all channels

## Project Structure

```
xgamma_gui_tool/
├── main.py                 # Entry point (can be run from root)
├── src/
│   ├── __init__.py
│   ├── main.py            # Main application entry point
│   ├── gamma_core.py      # Gamma management logic
│   ├── gui.py             # GUI implementation
│   ├── config_manager.py  # Autostart configuration
│   └── reference_image.py # Reference image generation
├── requirements.txt       # Python dependencies
├── gamma_adjust.desktop   # Desktop file template
└── assets/
    └── icons/             # Application icons
```

## Autostart

When you click "Save to Autostart", the application creates a desktop file in `~/.config/autostart/` that runs the xgamma command on system startup. The "Reset" button removes all xgamma-related entries from autostart.

## Error Handling

- If xgamma is not installed, the application will display a warning message with installation instructions and exit
- Invalid numeric inputs are automatically corrected
- Status messages appear in the status bar at the bottom of the window (no modal dialogs)

## License

This project is provided as-is for educational and mentoring purposes.

## Documentation

For xgamma command documentation, see:
https://yuweijun.github.io/manpages/man1/xgamma.1.html