# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Simple script to check figure spacing in fonts or UFOs (without kerning).
For each figure suffix found (such as .tosf), a new spacing page is made.

Input (pick one):
* folder(s) containing UFO- or font files
* individual UFO- or font files
* designspace file (for proofing UFO sources)

'''

import argparse
import subprocess

import drawBot as db

from fontParts.fontshell import RFont
from fontTools.ttLib import TTFont
from pathlib import Path

from .proofing_helpers.drawing import draw_glyph
from .proofing_helpers.files import get_font_paths, get_ufo_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.names import get_family_name, get_name_overlap
from .proofing_helpers.stamps import timestamp


def get_args():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        '--point_size',
        default=100,
        action='store',
        type=int,
        help='font size')

    parser.add_argument(
        '-s', '--suffixes',
        action='store',
        help='suffixes',
        nargs='*')

    parser.add_argument(
        'input',
        nargs='+',
        metavar='INPUT',
        help='input file(s) or folder(s)')

    return parser.parse_args()


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


def make_proof_pages(args, input_file):
    font_path = Path(input_file)

    if input_file.suffix.lower() == '.ufo':
        f = RFont(input_file)
        all_glyphs = f.keys()
        glyph_container = f
        upm = f.info.unitsPerEm
        glyph_order = f.glyphOrder
    else:
        f = TTFont(input_file)
        all_glyphs = f.getGlyphOrder()
        glyph_container = f.getGlyphSet()
        upm = f['head'].unitsPerEm
        glyph_order = f.getGlyphOrder()

    if not upm:
        upm = 1000

    footer = font_path.name
    if footer == 'font.ufo':
        footer += f' ({f.info.styleName})'

    suffixes = get_figure_suffixes(all_glyphs, args.suffixes)
    for suffix in suffixes:
        proof_text = make_proof_text(glyph_order, suffix)
        all_gnames = [gn for line in proof_text for gn in line]

        if set(all_gnames) <= set(glyph_order):
            db.newPage('A4Landscape')
            # A4Landscape: 842 x 505

            stamp = db.FormattedString(
                f'{footer} | {suffix} | {timestamp(readable=True)}',
                font=FONT_MONO,
                fontSize=10,
                align='right')

            db.textBox(stamp, (280, 20, 542, 20))
            MARGIN = 30
            x_offset = MARGIN
            y_offset = db.height() - MARGIN - args.point_size
            scale_factor = args.point_size / upm
            line_space = args.point_size * 1.2

            for line in proof_text:

                for gname in line:
                    with db.savedState():
                        glyph = glyph_container[gname]
                        db.translate(x_offset, y_offset)
                        db.scale(scale_factor)
                        draw_glyph(glyph)
                        x_offset += glyph.width * scale_factor
                x_offset = MARGIN
                y_offset -= line_space
        else:
            unsupported = sorted(set(all_gnames) - set(glyph_order))
            us_report = ", ".join(sorted(unsupported, key=all_gnames.index))
            print(f'{font_path.name} does not support {us_report}')


def make_proof_text(available_gnames, suffix=''):
    spacer = 'zero' + suffix
    if spacer not in available_gnames:
        spacer = 'zero'

    basic_figures = 'zero one two three four five six seven eight nine'.split()
    # some figures may not be necessary for all sets, e.g. a rounded zero
    # will likely be the same as a default zero. Therefore, if a given
    # suffixed figure does not exist, fall back to the default figure.
    suffixed_figures = [
        figure + suffix if
        figure + suffix in available_gnames else
        figure for figure in basic_figures]

    # one of both slashed zeros might exist
    if 'zero.slash' + suffix in available_gnames:
        suffixed_figures.insert(0, 'zero.slash' + suffix)
    elif 'zero' + suffix + '.slash' in available_gnames:
        suffixed_figures.insert(0, 'zero' + suffix + '.slash')

    output = []
    for line in chunks(suffixed_figures, 4):
        joined_line = [spacer] + list(joinit(line, spacer)) + [spacer]
        output.append(joined_line)
    return output


def get_figure_suffixes(gnames, custom_suffixes, report=False):
    figure_variants = set([
        gn for gn in gnames if '.' in gn and gn.split('.')[0] == 'three'])

    if custom_suffixes is None:
        suffixes = []
        if 'three' in gnames:
            # default, non-suffixed figures exist
            suffixes.append('')
        # all the other suffixes
        suffixes.extend(sorted([
            '.' + '.'.join(gn.split('.')[1:]) for gn in figure_variants]))

        if report:
            print('figure suffixes found:')
            for suffix in suffixes:
                if suffix == '':
                    print('(no suffix)')
                else:
                    print(suffix)
            print()

    else:
        suffixes = dot_suffixes(custom_suffixes)

    return suffixes


def make_output_name(paths):
    '''
    Make a sensible filename for the PDF proof created.

    '''
    chunks = ['figure spacing']

    all_family_names = sorted(set([get_family_name(font) for font in paths]))
    family_name_overlap = get_name_overlap(all_family_names)

    if family_name_overlap:
        chunks.append(family_name_overlap)
    else:
        if len(all_family_names) == 1:
            chunks.append(all_family_names[0])
        elif len(all_family_names) == 2:
            chunks.append(', '.join(all_family_names))
        else:
            chunks.append(', '.join(all_family_names[:2]) + ' etc')

    pdf_name = ' '.join(chunks) + '.pdf'
    return pdf_name


def main():
    args = get_args()

    input_paths = [Path(i) for i in args.input]
    input_list = []
    for input_path in input_paths:
        input_list.extend(get_ufo_paths(input_path))
        input_list.extend(get_font_paths(input_path))

    output_name = make_output_name(input_list)
    output_path = Path(f'~/Desktop/{output_name}').expanduser()

    db.newDrawing()
    for input_file in input_list:
        make_proof_pages(args, input_file)

    db.saveImage(output_path)
    db.endDrawing()

    subprocess.call(['open', output_path])


if __name__ == '__main__':
    main()
