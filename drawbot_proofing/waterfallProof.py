# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates pages of example words for a list of fonts, arranged in waterfall-like
fashion (both vertically and horizontally).

The proof text comes from the waterfall_horizontal and waterfall_vertical text
files found in the _content folder.

Input: folder containing font files.

'''

import argparse
import os
from pathlib import Path
import subprocess
import sys

import drawBot as db

from .proofing_helpers import fontSorter
from .proofing_helpers.files import get_font_paths, read_text_file


def get_options():
    parser = argparse.ArgumentParser(
        description=__doc__)

    parser.add_argument(
        'd',
        action='store',
        metavar='FOLDER',
        help='folder to crawl')

    parser.add_argument(
        '--date',
        default=False,
        action='store_true',
        help='date proof file')

    parser.add_argument(
        '--pointsize', '-p',
        action='store',
        default=40,
        type=int,
        help='point size')

    parser.add_argument(
        '-k', '--kerning_off',
        default=False,
        action='store_true',
        help='switch off kerning')

    parser.add_argument(
        '--onum',
        default=False,
        action='store_true',
        help='old-style figures')

    parser.add_argument(
        '--pnum',
        default=False,
        action='store_true',
        help='proportional figures')

    return parser.parse_args()


def main():
    args = get_options()
    if os.path.isdir(args.d):
        font_paths = get_font_paths(args.d)
        fonts = fontSorter.sort_fonts(font_paths)
    else:
        sys.exit('no fonts found')

    db.newDrawing()
    PT_SIZE = args.pointsize
    LEADING = PT_SIZE * 1.2
    MARGIN = 48

    v_content_path = os.path.join(
        os.path.dirname(__file__), '_content/waterfall_vertical.txt')
    h_content_path = os.path.join(
        os.path.dirname(__file__), '_content/waterfall_horizontal.txt')
    v_content = read_text_file(v_content_path)
    h_content = read_text_file(h_content_path)

    # Create a new page for each word in the vertical content text file:
    for line in v_content.split('\n'):

        feature_dict = {
            'kern': not args.kerning_off,
            'onum': args.onum,
            'pnum': args.pnum,
        }

        db.newPage('Legal')
        top_line = db.height() - PT_SIZE - MARGIN
        offset = top_line
        for f_index, font in enumerate(fonts):
            offset = top_line - f_index * LEADING
            fs = db.FormattedString(
                line,
                font=font,
                fontSize=PT_SIZE,
                openTypeFeatures=feature_dict,
            )

            db.text(fs, (MARGIN, offset))

    # Create a page with horizontal waterfall content:
    db.newPage('LegalLandscape')
    top_line = db.height() - PT_SIZE - MARGIN

    for word_index, word in enumerate(h_content.split('\n')):
        offset = top_line - word_index * LEADING

        fs = db.FormattedString(
            fontSize=PT_SIZE,
        )
        for font in fonts:
            fs.append(word, font=font)

        db.text(fs, (MARGIN, offset))

    dir_name = Path(args.d).name
    output_path = f'~/Desktop/waterfallProof ({dir_name}).pdf'
    db.saveImage(output_path)
    db.endDrawing()
    print(f'saved to {output_path}')
    subprocess.call(['open', os.path.expanduser(output_path)])


if __name__ == '__main__':
    main()
