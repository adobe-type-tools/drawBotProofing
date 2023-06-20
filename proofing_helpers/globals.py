# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

from pathlib import Path

_font_dir = Path(__file__).parents[1].joinpath('_fonts')
ADOBE_BLANK = _font_dir.joinpath('AdobeBlank.otf')
ADOBE_NOTDEF = _font_dir.joinpath('AND-Regular.otf')
FONT_MONO = _font_dir.joinpath('SourceCodePro-Regular.otf')
