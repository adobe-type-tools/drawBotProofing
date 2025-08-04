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
(`all`). Writing systems supported are `lat`, `grk`, `cyr`, and `figures`.

Input: one or more font files.

'''

import argparse
import subprocess

import drawBot as db
from pathlib import Path

from .proofing_helpers.files import get_font_paths, make_temp_font
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO, ADOBE_BLANK
from .proofing_helpers.stamps import timestamp


def get_options():

    mode_choices = ['proof', 'spacing', 'sample', 'all']
    ws_choices = ['lat', 'grk', 'cyr', 'figures', 'all']

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )

    parser.add_argument(
        '-m', '--mode',
        action='store',
        default='proof',
        choices=mode_choices,
        help='mode')

    parser.add_argument(
        '-w', '--writing_system',
        action='store',
        default='lat',
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
        '-d', '--date',
        action='store_true',
        help='date proof document')

    parser.add_argument(
        '-t', '--text',
        action='store',
        help='read custom file')

    parser.add_argument(
        'input',
        nargs='+',
        help='input font file(s)')

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


def make_proof(args, fonts, output_path):

    if args.text:
        text_path = Path(args.text)
        if text_path.exists():
            proof_text = read_text_file(text_path)

    else:
        mode = args.mode.lower()
        custom_string = args.string
        writing_system = args.writing_system.lower()
        proof_text = make_proof_text(mode, writing_system, custom_string)

    db.newDrawing()

    MARGIN = 30
    line_space = args.point_size * 1.2

    if len(fonts) == 1:
        tmp_fonts = fonts
    else:
        tmp_fonts = [
            make_temp_font(i, font) for (i, font) in enumerate(fonts)]

    for page in proof_text:

        feature_dict = {'kern': not args.kerning_off}
        # undocumented feature -- it is possible to add feature tags
        # to the input text files. Not sure how useful.
        #
        # if page.startswith('#'):  # features
        #     page_lines = page.splitlines()
        #     feature_line = page_lines[0].strip('#').strip()
        #     feature_dict = {
        #         feature_name: True for feature_name in feature_line.split()}
        #     page = '\n'.join(page_lines[1:])

        for font_index, font in enumerate(fonts):
            tmp_font = tmp_fonts[font_index]
            font_path = Path(font)
            db.newPage('LetterLandscape')

            fs_stamp = db.FormattedString(
                f'{font_path.name}',
                font=FONT_MONO,
                fontSize=10,
                align='right')
            if args.kerning_off:
                fs_stamp += ' | no kerning'
            fs_stamp += f' | {timestamp(readable=True)}'

            db.textBox(fs_stamp, (0, MARGIN, db.width() - MARGIN, 20))
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


def make_proof_text(mode, writing_system, custom_string=None):

    proof_text = []

    if custom_string:
        proof_text.extend([custom_string])
        proof_text.extend(read_sample_text(mode, 'lat'))

    else:
        proof_text.extend(read_sample_text(mode, writing_system))

    if writing_system not in ['all', 'figures']:
        # add the figures for good measure
        proof_text.extend(read_sample_text(mode, 'figures'))
    return proof_text


def make_pdf_name(args, fonts):
    '''
    Try to make a sensible filename for the PDF proof created.

    '''
    all_font_names = [font.name for font in fonts]
    font_name_string = ' vs '.join(all_font_names)

    if len(font_name_string) > 255:
        font_name_string = 'comparison of many fonts'

    name_chunks = [font_name_string, args.mode, args.writing_system]
    if args.date:
        name_chunks.insert(0, timestamp())

    return ' '.join(name_chunks) + '.pdf'


def main():
    args = get_options()

    fonts = []
    for item in args.input:
        fonts.extend(get_font_paths(item))

    output_pdf_name = make_pdf_name(args, fonts)
    output_path = Path(f'~/Desktop/{output_pdf_name}').expanduser()
    make_proof(args, fonts, output_path)
    subprocess.call(['open', output_path])


if __name__ == '__main__':
    main()
