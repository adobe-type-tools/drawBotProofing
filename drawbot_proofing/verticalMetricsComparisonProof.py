# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates pages with example characters to visualize the variation
of vertical metrics across a typeface family.

Input (pick one):
* folder(s) containing UFO files or font files
* individual UFO- or font files
* designspace file (for proofing UFO sources)

'''

import argparse
import defcon
import drawBot as db

from .verticalMetricsProof import (
    MARGIN, PT_SIZE, FontInfo, finish_drawing, report_metrics
)

from .proofing_helpers import fontSorter
from .proofing_helpers.files import get_font_paths, get_ufo_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.drawing import draw_glyph
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.names import get_style_name, get_ps_name


def get_args():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        'input',
        metavar='INPUT',
        nargs='+',
        help='input file(s) or folder(s)',
    )
    parser.add_argument(
        '-o', '--output_file_name',
        action='store',
        metavar='PDF',
        help='output file name')

    parser.add_argument(
        '-u', '--normalize_upm',
        action='store_true',
        default=False,
        help='convert label values to 1000 UPM-equivalent')

    parser.add_argument(
        '-s', '--sample_string',
        type=str,
        default='Hnxphlg',
        help='sample string')

    return parser.parse_args()


def draw_metrics_page_ufo(character, fo_list, cmap_list, normalize_upm=False):

    upm_list = [f.info.unitsPerEm for f in fo_list]
    height_list = [f.info.ascender - f.info.descender for f in fo_list]
    descender_list = [f.info.descender for f in fo_list]

    # get combined width of glyphs
    page_width = 0
    for i, fo in enumerate(fo_list):
        char_map = cmap_list[i]
        char_gname = char_map.get(ord(character), '.notdef')
        char_width = fo[char_gname].width
        page_width += char_width * PT_SIZE / fo.info.unitsPerEm
    page_width += 2 * MARGIN

    heights = [
        height_list[i] * PT_SIZE / upm_list[i]
        for i, fo in enumerate(fo_list)]
    descenders = [
        descender_list[i] * PT_SIZE / upm_list[i]
        for i, fo in enumerate(fo_list)]

    lowest_descender = min(descenders)
    page_height = max(heights) + 2 * MARGIN

    db.newPage(page_width, page_height)
    x_offset = MARGIN

    for i, font in enumerate(fo_list):
        upm = font.info.unitsPerEm
        scale_factor = PT_SIZE / upm
        baseline = (abs(lowest_descender) + MARGIN) / scale_factor
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

                    if normalize_upm and upm != 1000:
                        conversion_factor = 1000 / upm
                        label_value = f'{y_value * conversion_factor:.0f}'
                    else:
                        label_value = str(y_value)

                    db.font(FONT_MONO)
                    db.fontSize(6 / scale_factor)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        label_value,
                        (glyph.width / 2, y_value + 2 / scale_factor),
                        align='center')
                db.text(
                    get_style_name(font.path),
                    (glyph.width / 2, -baseline + (MARGIN / 2) / scale_factor),
                    align='center')


def draw_metrics_page_font(
    character, font_info_list, normalize_upm=False
):
    # Calculate width/height of the page.
    # Using local UPM values here, supporting different UPMs on the same line

    page_width = 0
    for fi in font_info_list:
        char_gname = fi.char_map.get(ord(character), '.notdef')
        char_width = fi.advance_widths.get(char_gname)
        page_width += char_width * PT_SIZE / fi.upm
    page_width += 2 * MARGIN

    heights = [
        (fi.ascender - fi.descender) * PT_SIZE / fi.upm
        for fi in font_info_list]
    descenders = [
        fi.descender * PT_SIZE / fi.upm for fi in font_info_list]

    lowest_descender = min(descenders)
    page_height = max(heights) + 2 * MARGIN

    db.newPage(page_width, page_height)
    x_offset = MARGIN

    for f_info in font_info_list:
        upm = f_info.upm
        scale_factor = PT_SIZE / upm
        baseline = (abs(lowest_descender) + MARGIN) / scale_factor

        line_y = (
            f_info.descender, 0, f_info.xHeight,
            f_info.capHeight, f_info.ascender
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
                    if normalize_upm and upm != 1000:
                        conversion_factor = 1000 / upm
                        label_value = f'{y_value * conversion_factor:.0f}'
                    else:
                        label_value = str(y_value)

                    db.font(FONT_MONO)
                    db.fontSize(6 / scale_factor)
                    # db.fill(0, 0.981, 0.574)  # Sea Foam
                    db.fill(1, 0.186, 0.573)  # Strawberry
                    db.text(
                        label_value,
                        (glyph_width / 2, y_value + 2 / scale_factor),
                        align='center')
                db.text(
                    get_style_name(f_info.path),
                    (glyph_width / 2, -baseline + (MARGIN / 2) / scale_factor),
                    align='center')


def process_font_paths(font_paths, args):
    font_list = fontSorter.sort_fonts(font_paths)
    font_info_list = [FontInfo(font_path, args) for font_path in font_list]
    extension = font_list[0].suffix.upper()
    family_name = font_info_list[0].familyName
    name_length = max([len(fi.ps_name) for fi in font_info_list])

    if args.output_file_name:
        doc_name = f'comparison {args.output_file_name}'
    else:
        doc_name = f'comparison {family_name} ({extension[1:]})'

    for f_info in font_info_list:
        report_metrics(f_info, 0, name_length)

    for char in args.sample_string:
        draw_metrics_page_font(
            char, font_info_list, args.normalize_upm)

    finish_drawing(doc_name)


def report_ufo_metrics(fo, name_width=20):
    '''
    report ps name, descender, baseline, x-height, cap height, ascender,
    '''

    format_dict = {
        'styleName': fo.info.styleName,
        'ps_name': (
            fo.info.postscriptFontName if fo.info.postscriptFontName else
            get_ps_name(fo.path)),
        'descender': fo.info.descender if fo.info.descender else 0,
        'xHeight': fo.info.xHeight if fo.info.xHeight else 0,
        'capHeight': fo.info.capHeight if fo.info.capHeight else 0,
        'ascender': fo.info.ascender if fo.info.ascender else 0,
    }
    print(
        f'{format_dict.get("ps_name"):{name_width}s} '
        f'{format_dict.get("descender"):>5d} 0 '
        f'{format_dict.get("xHeight"):>4d} '
        f'{format_dict.get("capHeight"):>4d} '
        f'{format_dict.get("ascender"):>4d} '
    )


def process_ufo_paths(ufo_paths, args):
    ufo_list = fontSorter.sort_fonts(ufo_paths)
    name_length = max([len(get_ps_name(f)) for f in ufo_list])

    fo_list = [defcon.Font(f) for f in ufo_list]
    cmap_list = [{g.unicode: g.name for g in f if g.unicode} for f in fo_list]

    family_name = fo_list[0].info.familyName
    if args.output_file_name:
        doc_name = f'comparison {args.output_file_name}'
    else:
        doc_name = f'comparison {family_name} (UFO)'

    for fo in fo_list:
        report_ufo_metrics(fo, name_length)

    for char in args.sample_string:
        draw_metrics_page_ufo(
            char, fo_list, cmap_list, args.normalize_upm)

    finish_drawing(doc_name)


def main():
    args = get_args()
    font_paths = []
    ufo_paths = []
    for p in args.input:
        ufo_paths.extend(get_ufo_paths(p))
        font_paths.extend(get_font_paths(p))

    if ufo_paths:
        process_ufo_paths(ufo_paths, args)

    elif font_paths:
        process_font_paths(font_paths, args)

    else:
        print('no fonts or UFOs found')


if __name__ == '__main__':
    main()
