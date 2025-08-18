# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Visualizes the complete glyphset of a font or UFO on a single page.
The output is good to use with a diffing tool like `diff-pdf` in a later step.

The glyphset can be filtered with a regular expression (for example,
use `-r ".*dieresis"` to show all glyphs whose names end with -dieresis).

Input (pick one):
* folder(s) containing UFO files or font files
* individual UFO- or font files
* designspace file (for proofing UFO sources)

'''

import argparse
import defcon
import drawBot as db
import re
import subprocess

from fontTools.ttLib import TTFont
from pathlib import Path
from .proofing_helpers.drawing import draw_glyph
from .proofing_helpers.files import get_font_paths, get_ufo_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.names import (
    get_ps_name, get_name_overlap, get_path_overlap)
from .proofing_helpers.stamps import timestamp


def get_args(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )

    parser.add_argument(
        'input',
        nargs='+',
        metavar='INPUT',
        help='file(s) or folder(s)')

    parser.add_argument(
        '-r', '--regex',
        action='store',
        default='',
        help='regex for glyph set filtering')

    parser.add_argument(
        '-c', '--columns',
        action='store',
        default=12,
        type=int,
        help='glyphs per line')

    parser.add_argument(
        '-s', '--stroke',
        action='store_true',
        default=False,
        help='draw a stroke around glyph boxes')

    return parser.parse_args(args)


def draw_glyph_box(g, origin, box_width, box_height, upm, scale=1):
    '''
    draw a glyph in a box, somewhere on the page
    '''
    x, y = origin
    f_height = upm
    f_descender = upm / 3 / scale
    scale_factor = box_height / f_height * scale
    with db.savedState():
        db.scale(
            scale_factor, scale_factor, center=origin)
        db.translate(*origin)
        db.translate(
            box_width / 2 / scale_factor - g.width / 2, abs(f_descender)
        )
        draw_glyph(g)


def draw_glyphset_page(f, glyph_list, caption, columns=12, stroke=False):
    doc_width = db.sizes()['TabloidLandscape'][0]
    margin = 10

    dflt_box_width = (doc_width - 2 * margin) / columns
    dflt_box_height = dflt_box_width
    margin_bottom = dflt_box_height + margin

    scale = .66
    scale_factor = dflt_box_height / 1000 * scale

    box_x = margin
    box_y = -margin

    if isinstance(f, TTFont):
        glyph_container = f.getGlyphSet()
        upm = f['head'].unitsPerEm
    else:
        glyph_container = f
        upm = f.info.unitsPerEm
    if not upm:
        upm = 1000

    # keep track of how many boxes we’ll need
    # (mainly, to calculate how tall the sample should be)
    boxes = []
    box_y -= dflt_box_height
    for g_index, gname in enumerate(glyph_list):
        box_width = dflt_box_width
        box_height = dflt_box_height

        glyph = glyph_container[gname]

        if (glyph.width / upm) * 1000 * scale_factor > box_width * .9:
            wide_box = box_width * 2
            while glyph.width * scale_factor >= wide_box:
                wide_box += box_width

            box_width = wide_box

        if box_x + box_width >= doc_width:
            box_x = margin
            box_y -= box_height

        origin = (box_x, box_y)
        boxes.append((origin, box_width, box_height))
        box_x += box_width

    last_box_origin = boxes[-1][0]
    doc_height = abs(last_box_origin[1]) + margin_bottom
    db.newPage(doc_width, doc_height)

    time_stamp = db.FormattedString(
        caption,
        font=FONT_MONO,
        fontSize=10,
        align='right')

    text_margin = 2 * margin
    db.textBox(
        time_stamp, (text_margin, margin, doc_width - 2 * text_margin, 20))

    for g_index, gname in enumerate(glyph_list):
        glyph = glyph_container[gname]
        box = boxes[g_index]
        # origin relative to top of document
        origin_relative, box_width, box_height = box
        origin = origin_relative[0], doc_height + origin_relative[1]

        # draw boxes
        if stroke:
            with db.savedState():
                db.fill(None)
                db.stroke(0)
                db.strokeWidth(.5)
                db.rect(*origin, box_width, box_height)

        draw_glyph_box(glyph, origin, box_width, box_height, upm, scale)


def filter_glyph_list(regex_string, glyph_list):
    '''
    filter list of glyphs by regular expression
    '''
    reg_ex = re.compile(regex_string)
    matches = list(filter(reg_ex.match, glyph_list))
    if matches:
        print('filtered glyph list:')
        print(' '.join(matches))
        glyph_list = matches
    else:
        print('no matches for regular expression')
        return []
    return glyph_list


def make_output_name(input_list, args):
    output_name = ['glyphsetProof']

    if args.regex:
        output_name.insert(0, 'filtered')

    if len(input_list) == 1:
        input_font = input_list[0]
        output_name.append(get_ps_name(input_font))
        output_name.append(f'({input_font.suffix.lstrip(".").upper()})')
    else:
        overlap = get_name_overlap([get_ps_name(f) for f in input_list])
        if not overlap:
            # at least the fonts must have a shared path
            overlap = get_path_overlap(input_list)
        output_name.append(overlap)

    return ' '.join(output_name) + '.pdf'


def make_glyphset_page(args, input_file):
    if input_file.suffix == '.ufo':
        f = defcon.Font(input_file)
        glyph_order = f.glyphOrder
        all_glyphs = f.keys()
        if set(glyph_order) == set(all_glyphs):
            complete_glyph_order = glyph_order
        else:
            # additional glyphs could be
            # - all glyphs (in case public.glyphOrder is empty)
            # - any glyphs not mentioned in public.glyphOrder
            additional_glyphs = set(all_glyphs) - set(glyph_order)
            complete_glyph_order = glyph_order + sorted(additional_glyphs)
    else:
        f = TTFont(input_file)
        complete_glyph_order = f.getGlyphOrder()

    if args.regex:
        glyph_list = filter_glyph_list(args.regex, complete_glyph_order)
    else:
        glyph_list = complete_glyph_order

    time_stamp = timestamp(readable=True)
    caption = f'{input_file.name} | {time_stamp}'.format()
    draw_glyphset_page(f, glyph_list, caption, args.columns, args.stroke)


def main(test_args=None):
    args = get_args(test_args)

    # collect input files
    input_list = []
    for input_path in args.input:
        input_list.extend(get_ufo_paths(input_path))
        input_list.extend(get_font_paths(input_path))

    db.newDrawing()
    for input_file in input_list:
        make_glyphset_page(args, input_file)

    output_name = make_output_name(input_list, args)
    output_path = Path(f'~/Desktop/{output_name}').expanduser()
    db.saveImage(output_path)
    subprocess.call(['open', output_path])
    db.endDrawing()


if __name__ == '__main__':
    main()
