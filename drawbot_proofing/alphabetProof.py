# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates example pages for:

- general alphabet (upper- and lowercase)
- spacing proofs
- some sample words

Modes (`proof`, `spacing`, `sample`) can be chosen individually, or all at once
(`all`).

Writing systems supported are `lat`, `grk`, `cyr`, and `figures`. By default,
supported writing systems are automatically chosen on a per-font basis.

Kerning can be toggled off (`-k`).

Optionally, a sample string (`-s`), or an input text file file (`-t`) can be
specified. When using an input a text file, there will be no reflow (which may
mean that lines exceed the right edge of the page). A double-line break in the
text file translates to a new page in the proof.

Input:
* font file(s), or folder(s) containing font files

'''

import argparse
import subprocess

import drawBot as db

from fontTools.ttLib import TTFont
from pathlib import Path

from .proofing_helpers import fonts as fonts_helper
from .proofing_helpers import fontSorter
from .proofing_helpers.files import get_font_paths
from .proofing_helpers.fonts import make_temp_font, supports_text
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO, ADOBE_BLANK
from .proofing_helpers.names import (
    get_name_overlap, get_path_overlap, get_ps_name, get_unique_name)
from .proofing_helpers.stamps import timestamp


def get_args():

    mode_choices = ['proof', 'spacing', 'sample', 'all']
    ws_choices = ['lat', 'grk', 'cyr', 'figures', 'auto']

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        '-m', '--mode',
        action='store',
        default='proof',
        choices=mode_choices,
        help='mode')

    parser.add_argument(
        '-w', '--writing_system',
        action='store',
        default='auto',
        choices=ws_choices,
        help='writing system')

    parser.add_argument(
        '-s', '--string',
        action='store',
        help='custom string',
        default=None,)

    parser.add_argument(
        '-p', '--point_size',
        default=60,
        action='store',
        type=int,
        help='font size')

    parser.add_argument(
        '-k', '--kerning_off',
        default=False,
        action='store_true',
        help='switch off kerning')

    parser.add_argument(
        '-t', '--text',
        action='store',
        help='read custom text file')

    parser.add_argument(
        'input',
        metavar='INPUT',
        nargs='+',
        help='font file(s) or folder(s)')

    return parser.parse_args()


def read_text_file(file_path):
    '''
    Read a custom text file.
    This file is expected to indicate page breaks with a double linebreak.
    '''
    with open(file_path, 'r') as blob:
        pages = blob.read().split('\n\n')
    return pages


def read_sample_text(kind='sample', w_system='lat'):

    if kind == 'all':
        chunks = []
        for option in ['proof', 'spacing', 'sample']:
            chunks.extend(read_sample_text(option, w_system))
        return chunks

    if w_system == 'all':
        chunks = []
        for system in ['lat', 'grk', 'cyr', 'figures']:
            chunks.extend(read_sample_text(kind, system))
        return chunks

    else:
        text_dir = Path(__file__).parent / '_content' / 'alphabet proof'
        text_file_name = f'{kind}_{w_system}.txt'
        text_path = text_dir / text_file_name

        if text_path.exists():
            with open(text_path, 'r') as tf:
                pages = tf.read().split('\n\n\n')

            chunks = []
            for page in pages:
                filtered_page = [
                    line for line in page.split('\n') if
                    line and not
                    line.strip().startswith('#')]
                if filtered_page:
                    chunks.append('\n'.join(filtered_page))

            return chunks
        else:
            print(text_path, 'does not exist')


def get_supported_writing_systems(font_file):
    f = TTFont(font_file)
    cmap = f['cmap']
    supported = []
    for ws_name in 'lat', 'grk', 'cyr':
        if getattr(fonts_helper, f'supports_{ws_name}')(cmap):
            supported.append(ws_name)
    return supported


def get_all_supported_writing_systems(font_files):
    '''
    collect all supported writing systems
    '''
    all_wss = []
    for ff in font_files:
        wss = get_supported_writing_systems(ff)
        new_wss = [ws for ws in wss if ws not in all_wss]
        all_wss.extend(new_wss)
    return all_wss


def make_proof(args, fonts, output_path):

    if args.text:
        text_path = Path(args.text)
        if text_path.exists():
            proof_text = read_text_file(text_path)
        else:
            print(f'{text_path} is not a valid path.')

    else:
        mode = args.mode.lower()
        custom_string = args.string

        if args.writing_system.lower() == 'auto':
            writing_systems = get_all_supported_writing_systems(fonts)
        else:
            writing_systems = [args.writing_system]

        proof_text = make_proof_text(mode, writing_systems, custom_string)

    MARGIN = 30
    line_space = args.point_size * 1.2
    feature_dict = {'kern': not args.kerning_off}

    # avoid PS name clash, and avoid making too many temp fonts
    tmp_fonts = [make_temp_font(i, font) for (i, font) in enumerate(fonts)]

    for page in proof_text:
        for font_index, font in enumerate(fonts):

            # check if more than 50% of the required text per page is supported
            if supports_text(font, page, 50):

                tmp_font = tmp_fonts[font_index]
                font_path = Path(font)
                db.newPage('LetterLandscape')

                caption = db.FormattedString(
                    f'{font_path.name}',
                    font=FONT_MONO,
                    fontSize=10,
                    align='right')
                caption += f' | {get_unique_name(font)}'
                if args.kerning_off:
                    caption += ' | no kerning'
                caption += f' | {timestamp(readable=True)}'

                db.textBox(caption, (0, MARGIN, db.width() - MARGIN, 20))
                y_offset = db.height() - MARGIN - args.point_size
                for line in page.split('\n'):

                    fs = db.FormattedString(
                        line,
                        font=tmp_font,
                        fontSize=args.point_size,
                        fallbackFont=ADOBE_BLANK,
                        openTypeFeatures=feature_dict,
                    )
                    db.text(fs, (MARGIN, y_offset))

                    if len(line) == 0:
                        y_offset -= line_space / 2
                    else:
                        y_offset -= line_space

    db.saveImage(output_path)
    db.endDrawing()


def make_proof_text(mode, writing_systems, custom_string=None):

    proof_text = []

    if 'figures' not in writing_systems:
        # figures are always proofed, but not twice
        writing_systems.append('figures')

    if custom_string:
        proof_text.extend([custom_string])

    for ws in writing_systems:
        proof_text.extend(read_sample_text(mode, ws))

    return proof_text


def make_pdf_name(args, fonts):
    '''
    Make a sensible filename for the PDF proof created.

    '''
    chunks = []

    if args.mode == 'proof':
        proof_name = 'alphabet proof'
    elif args.mode == 'all':
        proof_name = 'full proof'
    else:
        proof_name = f'{args.mode} proof'
    chunks.append(proof_name)

    all_font_names = [get_ps_name(font) for font in fonts]
    family_name = get_name_overlap(all_font_names)
    if not family_name:
        family_name = get_path_overlap(fonts)
    chunks.append(family_name)

    if args.writing_system != 'auto':
        chunks.append(f'({args.writing_system})')

    pdf_name = ' '.join(chunks) + '.pdf'
    return pdf_name


def main():
    args = get_args()
    fonts = []
    for item in args.input:
        if Path(item).exists():
            fonts.extend(get_font_paths(item))
        else:
            print(f'{item} is not a valid path')

    if fonts:
        sorted_fonts = fontSorter.sort_fonts(fonts)
        output_pdf_name = make_pdf_name(args, sorted_fonts)
        output_path = Path(f'~/Desktop/{output_pdf_name}').expanduser()
        make_proof(args, sorted_fonts, output_path)
        subprocess.call(['open', output_path])


if __name__ == '__main__':
    main()
