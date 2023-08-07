# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates pages with example characters to visualize the variation
of vertical metrics across a typeface family.

Input: folder containing font or UFO files.

'''

import defcon
import drawBot as db

from proofing_helpers import fontSorter
from proofing_helpers.files import get_font_paths, get_ufo_paths
from proofing_helpers.globals import FONT_MONO

from verticalMetricsProof import *

GLYPH_NAMES = list('Hnxphlg')


def draw_metrics_page_ufo(glyph_name, font_list, page_width=1000):
    scale_factor = PT_SIZE / 1000
    db.newPage(page_width, 250)
    x_offset = MARGIN / scale_factor
    baseline = db.height() / 3 / scale_factor

    for font in font_list:
        line_y = (
            font.info.descender,
            0,
            font.info.xHeight,
            font.info.capHeight,
            font.info.ascender
        )
        with db.savedState():
            db.scale(scale_factor)
            db.translate(x_offset, baseline)
            db.stroke(None)
            glyph = font[glyph_name]
            draw_glyph(glyph)
            x_offset += glyph.width
            with db.savedState():
                for y_value in line_y:
                    db.stroke(0)
                    db.strokeWidth(1)
                    db.line((0, y_value), (glyph.width, y_value))
            with db.savedState():
                for y_value in [v for v in line_y if v != 0]:
                    db.font(FONT_MONO)
                    db.fontSize(30)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        str(y_value),
                        (glyph.width / 2, y_value + 10),
                        align='center')
                db.text(
                    font.info.styleName,
                    (glyph.width / 2, - baseline + 20),
                    align='center')


def draw_metrics_page_font(glyph_name, font_info_list, page_width=1000):
    db.newPage(page_width, 250)
    upm = font_info_list[0].upm
    scale_factor = PT_SIZE / upm
    x_offset = MARGIN / scale_factor
    baseline = db.height() / 3 / scale_factor

    for f_info in font_info_list:

        line_y = (
            f_info.descender,
            0,
            f_info.xHeight,
            f_info.capHeight,
            f_info.ascender
        )
        character = f_info.reverse_char_map.get(glyph_name)
        with db.savedState():
            db.font(f_info.path)
            db.fontSize(f_info.upm)
            db.scale(scale_factor)
            db.translate(x_offset, baseline)
            db.text(
                character,
                (0, 0)
            )
            glyph_width = f_info.advance_widths[glyph_name]
            x_offset += glyph_width
            with db.savedState():
                for y_value in line_y:
                    db.stroke(0)
                    db.strokeWidth(1)
                    db.line((0, y_value), (glyph_width, y_value))
            with db.savedState():
                for y_value in [v for v in line_y if v != 0]:
                    db.font(FONT_MONO)
                    db.fontSize(30)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        str(y_value),
                        (glyph_width / 2, y_value + 10),
                        align='center')
                db.text(
                    f_info.styleName,
                    (glyph_width / 2, - baseline + 20),
                    align='center')


def process_font_paths(font_paths, args):
    font_list = fontSorter.sort_fonts(font_paths)
    font_info_list = [FontInfo(font_path, args) for font_path in font_list]
    extension = font_list[0].suffix.upper()
    family_name = font_info_list[0].familyName
    if args.output_file_name:
        doc_name = f'comparison {args.output_file_name}'
    else:
        doc_name = f'comparison {family_name} ({extension[1:]})'

    page_width = sum(
        [fi.cap_H_width * PT_SIZE / fi.upm for fi in font_info_list]
    ) + 2 * MARGIN

    for f_info in font_info_list:
        print('{:20s} {:>3d} 0 {:>3d} {:>3d} {:>3d}'.format(
            f_info.styleName,
            f_info.descender,
            f_info.xHeight,
            f_info.capHeight,
            f_info.ascender))

    for g_name in GLYPH_NAMES:
        draw_metrics_page_font(g_name, font_info_list, page_width)

    finish_drawing(doc_name)


def process_ufo_paths(ufo_paths, args):
    font_list = fontSorter.sort_fonts(ufo_paths)
    fo_list = [defcon.Font(f) for f in font_list]
    family_name = fo_list[0].info.familyName
    if args.output_file_name:
        doc_name = f'comparison {args.output_file_name}'
    else:
        doc_name = f'comparison {family_name} (UFO)'
    page_width = sum(
        [fo['H'].width * PT_SIZE / 1000 for fo in fo_list]
    ) + 2 * MARGIN

    for fo in fo_list:
        print('{:20s} {:>3d} 0 {:>3d} {:>3d} {:>3d}'.format(
            fo.info.styleName,
            fo.info.descender,
            fo.info.xHeight,
            fo.info.capHeight,
            fo.info.ascender))

    for g_name in GLYPH_NAMES:
        draw_metrics_page_ufo(g_name, fo_list, page_width)

    finish_drawing(doc_name)


if __name__ == '__main__':
    args = get_options(description=__doc__)
    font_paths = get_font_paths(args.input_dir)
    ufo_paths = get_ufo_paths(args.input_dir)

    if ufo_paths:
        process_ufo_paths(ufo_paths, args)

    elif font_paths:
        process_font_paths(font_paths, args)

    else:
        print('no fonts or UFOs found')
