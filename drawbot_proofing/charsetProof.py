# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Visualizes a given (Adobe) character set.
The default charset is AL-3. Code points not supported in the font at hand will
be shown as a .notdef glyph (but are still present as text in the PDF file).

More information on Adobe’s character sets:

- [Latin](https://github.com/adobe-type-tools/adobe-latin-charsets)
- [Cyrillic](https://github.com/adobe-type-tools/adobe-cyrillic-charsets)
- [Greek](https://github.com/adobe-type-tools/adobe-greek-charsets)

Input: font file(s) or folder of fonts.

'''

import argparse
import subprocess
import drawBot as db

from pathlib import Path
from .proofing_helpers import fontSorter, charsets
from .proofing_helpers.files import get_font_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import ADOBE_NOTDEF
from .proofing_helpers.names import get_name_overlap


def get_args(args=None):
    available_charsets = [
        cs.upper() for cs in dir(charsets) if not cs.startswith('_')]

    parser = argparse.ArgumentParser(
        description=(__doc__),
        formatter_class=RawDescriptionAndDefaultsFormatter,
    )

    parser.add_argument(
        'input',
        metavar='INPUT',
        nargs='+',
        help='font file(s) or folder(s)'
    )
    parser.add_argument(
        '-p', '--pointsize',
        metavar='PT',
        action='store',
        default=40,
        type=int,
        help='point size for sample'
    )
    parser.add_argument(
        '-s', '--spacer',
        action='store',
        metavar='CHR',
        default='',
        help=r'spacing character (may need to be escaped with \)'
    )
    parser.add_argument(
        '-c', '--charset',
        action='store',
        default='AL3',
        # choices=available_charsets,  # ugly
        help=f'character set ({", ".join(available_charsets)})',
    )

    return parser.parse_args(args)


def draw_charset_page(font_path, args):
    pt_size = args.pointsize
    line_height = args.pointsize * 1.4
    content = getattr(charsets, args.charset.lower())
    spacer = args.spacer
    margin = args.pointsize / 2
    if spacer != '':
        content = spacer.join(content)
    content = '\u200B'.join(content)  # zw space

    db.newPage('A4')
    top_line = db.height() - margin - line_height
    line_y = top_line

    while content:
        fs = db.FormattedString(
            content,
            font=font_path,
            fontSize=pt_size,
            fallbackFont=ADOBE_NOTDEF,
        )
        if line_y < 0 and content:
            db.newPage('A4')
            line_y = top_line

        text_rect = (margin, line_y, db.width() - 2 * margin, line_height)
        content = db.textBox(fs, text_rect)
        line_y -= line_height


def make_output_filename(args, font_list):
    if len(font_list) > 1:
        base_names = [fn.stem for fn in font_list]
        name_overlap = get_name_overlap(base_names)
        return f'{len(font_list)} charsets {args.charset} {name_overlap}.pdf'
    else:
        font_file = font_list[0]
        return f'charset {args.charset} {font_file.stem}.pdf'


def main(test_args=None):
    args = get_args()
    font_list = []
    for input_path in args.input:
        font_list.extend(get_font_paths(input_path))

    if font_list:
        sorted_font_list = fontSorter.sort_fonts(font_list)
        db.newDrawing()
        for f_path in sorted_font_list:
            draw_charset_page(f_path, args)

        output_filename = make_output_filename(args, sorted_font_list)
        output_path = Path(f'~/Desktop/{output_filename}').expanduser()

        db.saveImage(output_path)
        db.endDrawing()
        subprocess.call(['open', output_path])

    else:
        print('No fonts (OTF or TTF) found.')


if __name__ == '__main__':
    main()
