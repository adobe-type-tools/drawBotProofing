# Installation Guide

This guide explains how to install the DrawBot Proofing Tools package.


## Before Installation

- generally, we recommend using a Python virtual environment. If you’d like to use one, you can easily create and activate one with the following commands in Terminal:

```bash
python3 -m venv my_venv
source my_venv/bin/activate
```


## Installation

### Option 1: Install from GitHub (Recommended)

```bash
pip install git+https://github.com/adobe-type-tools/drawBotProofing.git
```

### Option 2: Install from Local Source

If you have cloned or downloaded the repository:

```bash
# Navigate to the repository directory
cd drawBotProofing

# Install in development mode (for development)
pip install -e .

# Or install normally
pip install .
```


## Requirements

- Python 3.11 or higher
- macOS (required for DrawBot)


## Dependencies

The package will automatically install the following dependencies:
- `defcon`
- `drawbot` (from GitHub)
- `fonttools`
- `fontParts`
- `unicodedataplus`


## Troubleshooting

### DrawBot Installation Issues

If you encounter issues with DrawBot installation, make sure you're on macOS and have the latest version of pip:

```bash
pip install --upgrade pip
```

### Missing Dependencies

If you get import errors, try reinstalling with force-reinstall:

```bash
pip install --force-reinstall git+https://github.com/adobe-type-tools/drawBotProofing.git
```

### Command Not Found

If the commands are not found after installation, make sure your Python scripts directory is in your PATH, or try:

```bash
python -m pip install --user git+https://github.com/adobe-type-tools/drawBotProofing.git
```

Then restart your terminal.


## Development Installation

For development work:

```bash
git clone https://github.com/adobe-type-tools/drawBotProofing.git
cd drawBotProofing
pip install -e .
```

This installs the package in "editable" mode, so changes to the source code are immediately reflected.


## Uninstallation

To remove the package:

```bash
pip uninstall drawbot-proofing
``` 