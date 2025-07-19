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

Input: folder containing UFO or font files, individual fonts or UFOs.

'''

import argparse
import defcon
import drawBot as db
import re
import subprocess

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from pathlib import Path
from proofing_helpers.drawing import draw_glyph
from proofing_helpers.files import get_ufo_paths, get_font_paths
from proofing_helpers.globals import FONT_MONO
from proofing_helpers.names import get_ps_name
from proofing_helpers.stamps import timestamp


def get_args(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__)

    parser.add_argument(
        'input',
        nargs='+',
        help='file(s) or folder(s)')

    parser.add_argument(
        '-r', '--regex',
        action='store',
        default='',
        help='regex for glyph set filtering')

    parser.add_argument(
        '-s', '--stroke',
        action='store_true',
        default=False,
        help='draw a stroke around glyph boxes')

    return parser.parse_args(args)


def get_y_bounds(glyphset):
    '''
    get vertical metrics for a fonttools font

    XXX this may leads to differently-scaled fonts within the
    same family, since not all necessarily have the same bounding box.
    '''
    y_bounds = []
    bpen = BoundsPen(glyphset)
    for gname, glyph in glyphset.items():
        glyph.draw(bpen)
        _, y_bot, _, y_top = bpen.bounds
        y_bounds.append(y_bot)
        y_bounds.append(y_top)
    return min(y_bounds), max(y_bounds)


def draw_glyph_box(g, origin, box_width, box_height, upm, scale=1):
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


def draw_glyphset_page(f, glyph_list, stroke=False):
    doc_width = db.sizes()['TabloidLandscape'][0]
    margin = 10
    whitespace_bottom = margin * 10
    glyphs_per_line = 12

    dflt_box_width = (doc_width - 2 * margin) / glyphs_per_line
    dflt_box_height = dflt_box_width

    scale = .66
    scale_factor = dflt_box_height / 1000 * scale

    # xxx this does not deal with double- or triple-wide glyphs
    lines = len(glyph_list) // glyphs_per_line
    doc_height = lines * dflt_box_height + 2 * margin + whitespace_bottom

    box_x = margin
    box_y = doc_height - margin
    db.newPage(doc_width, doc_height)

    time_stamp = db.FormattedString(
        '{}'.format(timestamp(readable=True)),
        font=FONT_MONO,
        fontSize=10,
        align='right')

    text_margin = 2 * margin
    db.textBox(
        time_stamp, (text_margin, margin, doc_width - 2 * text_margin, 20))

    if isinstance(f, TTFont):
        glyph_container = f.getGlyphSet()
        upm = f['head'].unitsPerEm
    else:
        glyph_container = f
        upm = f.info.unitsPerEm
    if not upm:
        upm = 1000

    box_y -= dflt_box_height
    for g_index, gname in enumerate(glyph_list):
        box_width = dflt_box_width
        box_height = dflt_box_height

        glyph = glyph_container[gname]

        if glyph.width * scale_factor > box_width * .8:

            wide_box = box_width * 2
            while glyph.width * scale_factor >= wide_box:
                wide_box += box_width

            box_width = wide_box

        if box_x + box_width >= doc_width:
            box_x = margin
            box_y -= box_height

        origin = (box_x, box_y)

        # draw boxes
        if stroke:
            with db.savedState():
                db.fill(None)
                db.stroke(0)
                db.strokeWidth(.5)
                db.rect(*origin, box_width, box_height)

        draw_glyph_box(glyph, origin, box_width, box_height, upm, scale)
        box_x += box_width


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


def make_output_name(input_file, args):
    name = ['glyphsetProof']

    if args.regex:
        name.insert(0, 'filtered')

    name.append(get_ps_name(input_file))
    name.append(f'({input_file.suffix.lstrip(".").upper()})')

    return ' '.join(name) + '.pdf'


def make_glyphset_pdf(args, input_file):
    db.newDrawing()
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

    output_name = make_output_name(input_file, args)
    output_path = Path(f'~/Desktop/{output_name}').expanduser()

    draw_glyphset_page(f, glyph_list, args.stroke)
    db.saveImage(output_path)
    db.endDrawing()
    subprocess.call(['open', output_path])


def main(test_args=None):
    args = get_args(test_args)

    # collect input files
    input_list = []
    for input_path in args.input:
        input_list.extend(get_ufo_paths(input_path))
        input_list.extend(get_font_paths(input_path))

    for input_file in input_list:
        make_glyphset_pdf(args, input_file)


if __name__ == '__main__':
    main()
