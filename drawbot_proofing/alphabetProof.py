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

import os

import argparse
import subprocess

import drawBot as db

from .proofing_helpers.stamps import timestamp
from .proofing_helpers.files import get_font_paths, make_temp_font
from .proofing_helpers.fontSorter import sort_fonts


class RawDescriptionAndDefaultsFormatter(
    # https://stackoverflow.com/a/18462760
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter
):
    pass


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
        assets_path = os.path.dirname(__file__)
        text_dir = os.path.join(assets_path, '_content', 'alphabet proof')
        text_file_name = f'{kind}_{w_system}.txt'
        text_path = os.path.join(assets_path, text_dir, text_file_name)

        if os.path.exists(text_path):
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


def make_proof(args, input_paths, output_path):

    if args.text:
        if os.path.exists(args.text):
            proof_text = read_text_file(args.text)

    else:
        mode = args.mode.lower()
        custom_string = args.string
        writing_system = args.writing_system.lower()
        proof_text = make_proof_text(mode, writing_system, custom_string)

    db.newDrawing()

    assets_path = os.path.dirname(__file__)
    ADOBE_BLANK = db.installFont(os.path.join(
        assets_path, '_fonts/AdobeBlank.otf'))
    FONT_MONO = os.path.join(
        assets_path, '_fonts/SourceCodePro-Regular.otf')
    MARGIN = 30
    line_space = args.point_size * 1.2
    base_names = [os.path.basename(font) for font in input_paths]

    if len(input_paths) == 1:
        font_paths = input_paths
    else:
        font_paths = [
            make_temp_font(input_index, input_path) for
            (input_index, input_path) in enumerate(input_paths)]

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

        for font_index, font in enumerate(font_paths):
            font_name = base_names[font_index]
            db.newPage('LetterLandscape')

            fs_stamp = db.FormattedString(
                f'{font_name}',
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
                    font=font,
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


def get_input_paths(input_args):
    '''
    Find if the input argument is a folder or a/multiple file(s).
    Return either just the file, or get font paths within folders.

    '''
    if len(input_args) == 1 and os.path.isdir(input_args[-1]):
        return sort_fonts(get_font_paths(input_args[-1]), True)
    return input_args


def make_output_name(args):
    '''
    Try to make a sensible filename for the PDF proof created.

    '''
    if len(args.input) == 1 and os.path.isdir(args.input[-1]):
        input_paths = get_font_paths(args.input[-1])
    else:
        input_paths = args.input
    all_font_names = [
        os.path.splitext(os.path.basename(font))[0] for font in input_paths
    ]
    font_name_string = ' vs '.join(all_font_names)

    if len(font_name_string) > 200:
        font_name_string = 'comparison of many fonts'

    name_chunks = [font_name_string, args.mode, args.writing_system]
    if args.date:
        name_chunks.insert(0, timestamp())

    return ' '.join(name_chunks) + '.pdf'


def main():
    args = get_options()
    input_paths = get_input_paths(args.input)
    output_path = (os.path.join(
        os.path.expanduser('~/Desktop'),
        make_output_name(args)))
    make_proof(args, input_paths, output_path)
    subprocess.call(['open', output_path])


if __name__ == '__main__':
    main()
