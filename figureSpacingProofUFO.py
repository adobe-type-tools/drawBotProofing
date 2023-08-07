# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Simple script check figure spacing in UFOs (without kerning).
For each figure suffix (such as .tosf), a new spacing page is made.

Input: single UFO or folder containing UFO files.

'''

import os

import argparse
import subprocess

import drawBot as db

from fontParts.fontshell import RFont

from proofing_helpers.drawing import draw_glyph
from proofing_helpers.files import get_ufo_paths
from proofing_helpers.globals import FONT_MONO
from proofing_helpers.stamps import timestamp


def joinit(iterable, delimiter):
    '''
    https://stackoverflow.com/a/5656097
    '''
    it = iter(iterable)
    yield next(it)
    for x in it:
        yield delimiter
        yield x


def chunks(lst, n):
    '''
    Yield successive n-sized chunks from lst.
    https://stackoverflow.com/a/312464
    '''
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def dot_suffixes(suffix_list):
    '''
    make sure suffixes start with dots
    '''
    dotted_suffix_list = []
    for suffix in suffix_list:
        if suffix != '' and not suffix.startswith('.'):
            suffix = '.' + suffix
        dotted_suffix_list.append(suffix)
    return dotted_suffix_list


def make_page(args, font, suffix):
    proof_text = make_proof_text(font.glyphOrder, suffix)
    all_gnames = set([gn for line in proof_text for gn in line])

    if set(all_gnames) <= set(font.keys()):
        db.newPage('A4Landscape')
        # A4Landscape: 842 x 505

        stamp = db.FormattedString(
            '{} | {} | {}'.format(
                os.path.basename(font.path),
                suffix,
                timestamp(readable=True)),
            font=FONT_MONO,
            fontSize=10,
            align='right')

        db.textBox(stamp, (280, 20, 542, 20))
        MARGIN = 30
        x_offset = MARGIN
        y_offset = db.height() - MARGIN - args.point_size
        scale_factor = args.point_size / 1000
        line_space = args.point_size * 1.2

        for line in proof_text:

            for gname in line:
                with db.savedState():
                    glyph = font[gname]
                    db.translate(x_offset, y_offset)
                    db.scale(scale_factor)
                    draw_glyph(glyph)
                    x_offset += glyph.width * scale_factor
            x_offset = MARGIN
            y_offset -= line_space
    else:
        not_supported = sorted(set(all_gnames) - set(font.keys()))
        print(
            f'{", ".join(sorted(not_supported))}\n'
            f'not in {font.info.styleName}')


def make_proof_text(available_gnames, suffix=''):
    spacer = 'zero' + suffix
    basic_figures = 'zero one two three four five six seven eight nine'.split()
    figures = [figure + suffix for figure in basic_figures]
    output = []

    # brittle
    if suffix == '' and 'zero.slash' in available_gnames:
        figures.insert(0, 'zero.slash')
    if suffix == '.lf' and 'zero.lfslash' in available_gnames:
        figures.insert(0, 'zero.lfslash')

    for line in chunks(figures, 4):
        joined_line = [spacer] + list(joinit(line, spacer)) + [spacer]
        output.append(joined_line)
    return output


def get_options():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--point_size',
        default=100,
        action='store',
        type=int,
        help='font size',
    )

    parser.add_argument(
        '-s', '--suffixes',
        action='store',
        help='suffixes',
        nargs='*',
    )

    parser.add_argument(
        'path',
        help='folder containing UFO file(s)')

    return parser.parse_args()


if __name__ == '__main__':

    args = get_options()
    ufos = get_ufo_paths(args.path)
    ufos.sort()
    base_path = os.path.basename(os.path.normpath(args.path))
    output_path = (
        f'~/Desktop/figure spacing {base_path}.pdf'
    )

    fonts = [RFont(ufo) for ufo in ufos]
    if fonts:
        figure_variants = set([
            gn for f in fonts for gn in f.keys() if
            '.' in gn and
            gn.split('.')[0] == 'three'])

        if args.suffixes is None:
            suffixes = [''] + sorted(
                ['.' + gn.split('.')[-1] for gn in figure_variants])

            print('figure suffixes found:')
            for suffix in suffixes:
                if suffix == '':
                    print('(no suffix)')
                else:
                    print(suffix)
            print()

        else:
            suffixes = dot_suffixes(args.suffixes)

        db.newDrawing()
        for font in fonts:
            for suffix in suffixes:
                make_page(args, font, suffix)
        db.saveImage(output_path)
        db.endDrawing()

        subprocess.call(['open', os.path.expanduser(output_path)])

    else:
        print(f'no UFOs found in {args.path}')
