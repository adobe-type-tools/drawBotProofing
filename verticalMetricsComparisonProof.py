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

from verticalMetricsProof import (
    MARGIN, PT_SIZE,
    FontInfo,
    finish_drawing, get_options)

from proofing_helpers import fontSorter
from proofing_helpers.files import get_font_paths, get_ufo_paths
from proofing_helpers.drawing import draw_glyph
from proofing_helpers.globals import FONT_MONO


EXAMPLE_CHARS = list('Hnxphlg')


def draw_metrics_page_ufo(character, fo_list, cmap_list, page_width=1000):

    db.newPage(page_width, 250)
    x_offset = MARGIN

    for i, font in enumerate(fo_list):
        scale_factor = PT_SIZE / font.info.unitsPerEm
        baseline = db.height() / 3 / scale_factor
        line_y = (
            font.info.descender if font.info.descender else -250,
            0,
            font.info.xHeight if font.info.xHeight else 500,
            font.info.capHeight if font.info.capHeight else 750,
            font.info.ascender if font.info.ascender else 750
        )
        char_map = cmap_list[i]
        glyph_name = char_map.get(ord(character))
        with db.savedState():
            db.scale(scale_factor)
            db.translate(x_offset / scale_factor, baseline)
            db.stroke(None)
            glyph = font[glyph_name]
            draw_glyph(glyph)
            x_offset += glyph.width * scale_factor
            with db.savedState():
                for y_value in line_y:
                    db.stroke(0)
                    db.strokeWidth(1)
                    db.line((0, y_value), (glyph.width, y_value))
            with db.savedState():
                for y_value in [v for v in line_y if v != 0]:
                    db.font(FONT_MONO)
                    db.fontSize(6 / scale_factor)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        str(y_value),
                        (glyph.width / 2, y_value + 2 / scale_factor),
                        align='center')
                db.text(
                    font.info.styleName,
                    (glyph.width / 2, -baseline + 4 / scale_factor),
                    align='center')


def draw_metrics_page_font(character, font_info_list, page_width=1000):

    db.newPage(page_width, 250)
    x_offset = MARGIN

    for f_info in font_info_list:
        upm = f_info.upm
        scale_factor = PT_SIZE / upm
        baseline = db.height() / 3 / scale_factor

        line_y = (
            f_info.descender,
            0,
            f_info.xHeight,
            f_info.capHeight,
            f_info.ascender
        )
        glyph_name = f_info.char_map.get(ord(character))
        with db.savedState():
            db.font(f_info.path)
            db.fontSize(f_info.upm)
            db.scale(scale_factor)
            db.translate(x_offset / scale_factor, baseline)
            db.text(
                character,
                (0, 0)
            )
            glyph_width = f_info.advance_widths[glyph_name]
            x_offset += glyph_width * scale_factor
            with db.savedState():
                for y_value in line_y:
                    db.stroke(0)
                    db.strokeWidth(1)
                    db.line((0, y_value), (glyph_width, y_value))
            with db.savedState():
                for y_value in [v for v in line_y if v != 0]:
                    db.font(FONT_MONO)
                    db.fontSize(6 / scale_factor)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        str(y_value),
                        (glyph_width / 2, y_value + 2 / scale_factor),
                        align='center')
                db.text(
                    f_info.styleName,
                    (glyph_width / 2, - baseline + 4 / scale_factor),
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

    for char in EXAMPLE_CHARS:
        draw_metrics_page_font(char, font_info_list, page_width)

    finish_drawing(doc_name)


def process_ufo_paths(ufo_paths, args):
    font_list = fontSorter.sort_fonts(ufo_paths)
    fo_list = [defcon.Font(f) for f in font_list]
    upm_list = [f.info.unitsPerEm for f in fo_list]
    cmap_list = [{g.unicode: g.name for g in f if g.unicode} for f in fo_list]
    gnames_H = [cmap.get(ord('H')) for cmap in cmap_list]

    family_name = fo_list[0].info.familyName
    if args.output_file_name:
        doc_name = f'comparison {args.output_file_name}'
    else:
        doc_name = f'comparison {family_name} (UFO)'
    # get combined width of Hs – no matter which glyph name or UPM they have
    page_width = sum(
        [fo[gnames_H[i]].width * PT_SIZE / upm_list[i] for i, fo in enumerate(fo_list)]
    ) + 2 * MARGIN

    for fo in fo_list:
        # terminal feedback
        format_dict = {
            'styleName': fo.info.styleName,
            'descender': fo.info.descender if fo.info.descender else 0,
            'xHeight': fo.info.xHeight if fo.info.xHeight else 0,
            'capHeight': fo.info.capHeight if fo.info.capHeight else 0,
            'ascender': fo.info.ascender if fo.info.ascender else 0,
        }

        print('{:20s} {:>3d} 0 {:>3d} {:>3d} {:>3d}'.format(
            format_dict.get('styleName'),
            format_dict.get('descender'),
            format_dict.get('xHeight'),
            format_dict.get('capHeight'),
            format_dict.get('ascender')))

    for char in EXAMPLE_CHARS:
        draw_metrics_page_ufo(char, fo_list, cmap_list, page_width)

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
