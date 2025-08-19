# Installation Guide

This guide explains how to install the DrawBot Proofing Tools package.

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

## Available Commands

After installation, the following commands will be available:

### Proofing Tools accepting fonts and UFOs:
- `glyph-proof` - compare glyphs
- `glyphset-proof` - the whole glyphset on one page
- `figure-spacing-proof` - compare figure spacing proofs
- `vertical-metrics-comparison-proof` - compare vertical metrics across fonts

### Proofing Tools accepting fonts:
- `accent-proof` - check accents and their use accent proofs
- `alphabet-proof` - various basic proofs for different writing systems
- `charset-proof` - check for a given charset on one page
- `context-proof` - see characters in context
- `text-proof` - pages with example paragraphs
- `unicode-chart-proof` - generate Unicode character charts
- `vertical-metrics-proof` - visualize vertical metrics
- `waterfall-proof` - create various waterfalls

### Other Proofing Tools:
- `overlay-font-proof` - overlay two fonts
- `reference-proof` - compare multiple fonts side by side

## Quick Start

After installation, you can start using the tools immediately:

```bash
# Create a text proof using a font
text-proof -f /path/to/your/font.otf -c al3

# Get help for any command
text-proof --help
alphabet-proof --help
```

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