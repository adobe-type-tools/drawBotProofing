# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates simple view which illustrates all vertical metrics
set in the font metadata. Additionally, tallest and lowest glyphs are shown.

Using the -e option, the number of reported extreme glyphs can be modified.

Input:
* font file(s), or folder(s) containing font files

'''

import argparse
from pathlib import Path
import subprocess
import sys

import drawBot as db
from fontTools.pens.boundsPen import BoundsPen
from fontTools import ttLib

from .proofing_helpers import fontSorter
from .proofing_helpers.drawing import draw_glyph
from .proofing_helpers.files import get_font_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.names import (
    get_name_overlap, get_path_overlap, get_ps_name)

IN_UI = 'drawBot.ui' in sys.modules

if IN_UI:
    from vanilla.dialogs import getFileOrFolder  # noqa: F401

PT_SIZE = 200
MARGIN = 20
MARGIN_L = 6 * MARGIN


def get_args():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        'input',
        metavar='INPUT',
        nargs='+',
        help='font file(s) or folder(s)',
    )
    parser.add_argument(
        '-o', '--output_file_name',
        action='store',
        metavar='PDF',
        help='output file name')

    parser.add_argument(
        '-e', '--extremes',
        type=int,
        default=1,
        metavar='INT',
        help='number of extreme glyphs')

    parser.add_argument(
        '-u', '--normalize_upm',
        action='store_true',
        default=False,
        help='convert label values to 1000 UPM-equivalent')

    parser.add_argument(
        '-s', '--sample_string',
        type=str,
        default='Hxbpg',
        help='sample string')

    return parser.parse_args()


class FontInfo(object):

    def __init__(self, font_path, args):
        self.path = font_path.resolve()
        self.ttf = ttLib.TTFont(self.path)
        self.glyph_set = self.ttf.getGlyphSet()
        self.ascender = 0
        self.descender = 0
        self.xHeight = 0
        self.capHeight = 0
        self.sample_string = args.sample_string
        self.parse_cmap()
        self.extract_vertical_metrics()
        if hasattr(args, 'extremes'):
            # comparison proof does not need extremes
            self.extract_extreme_n_glyphs(n=args.extremes)

        self.extract_names()
        self.extract_widths()
        self.extract_upm()
        # sTypoAscender
        # sTypoDescender
        # sxHeight
        # sCapHeight

    def extract_upm(self):
        head_table = self.ttf['head']
        self.upm = head_table.unitsPerEm

    def extract_names(self):
        self.ps_name = get_ps_name(self.path)
        try:
            self.familyName, self.styleName = self.ps_name.split('-')
        except ValueError:
            self.familyName = self.ps_name
            self.styleName = '(None)'

    def extract_vertical_metrics(self):
        os2_table = self.ttf['OS/2']
        self.ascender = os2_table.sTypoAscender
        self.descender = os2_table.sTypoDescender
        self.typoLineGap = os2_table.sTypoLineGap
        self.xHeight = os2_table.sxHeight
        self.capHeight = os2_table.sCapHeight
        self.winAscent = os2_table.usWinAscent
        self.winDescent = os2_table.usWinDescent
        hhea_table = self.ttf['hhea']
        self.hheaAscender = hhea_table.ascender
        self.hheaDescender = hhea_table.descender

    def extract_extreme_n_glyphs(self, n=1):
        '''
        Gets n extreme glyphs for the sample
        '''
        dict_top = {}
        dict_bot = {}
        for glyph_name in self.ttf.getGlyphOrder():
            pen = BoundsPen(self.glyph_set)
            self.glyph_set[glyph_name].draw(pen)
            if pen.bounds:
                _, y_bot, _, y_top = pen.bounds
                dict_top.setdefault(y_top, []).append(glyph_name)
                dict_bot.setdefault(y_bot, []).append(glyph_name)
        y_maxs = sorted(dict_top, reverse=True)[0:n]
        y_mins = sorted(dict_bot)[0:n]
        self.g_ymax = [dict_top[v][0] for v in y_maxs]
        self.g_ymin = [dict_bot[v][0] for v in y_mins]

    def extract_widths(self):
        hmtx_table = self.ttf['hmtx']
        self.advance_widths = {g_name: w_record[0] for (
            g_name, w_record) in hmtx_table.metrics.items()
        }

    def get_bounds(self, glyph_name):
        pen = BoundsPen(self.glyph_set)
        self.glyph_set[glyph_name].draw(pen)
        return pen.bounds

    def parse_cmap(self):
        cmap_table = self.ttf['cmap']
        self.char_map = cmap_table.getBestCmap()
        self.reverse_char_map = {
            gname: chr(c_index) for c_index, gname in self.char_map.items()
        }

def get_glyph_names(font_info):
    '''
    Collect some standard glyphs defining basic metrics,
    as well as tallest and lowest glyphs.
    '''
    glyph_names = [
        font_info.char_map.get(ord(char)) for
        char in font_info.sample_string]
    glyph_names += font_info.g_ymin
    glyph_names += font_info.g_ymax
    return glyph_names


def get_string_bounds(f_info, glyph_names):
    '''
    Calculate the width and height of the string (including swashy letters,
    which may extend to the right further than their advance width, and incl.
    glyphs which may exceed any pre-set vertical metrics).
    '''
    insertion_point = 0
    x_extent = []
    # vertical metrics may exceed any outline bounds:
    y_extent = [f_info.winDescent, f_info.winAscent]

    for gn in glyph_names:
        g_width = f_info.advance_widths.get(gn, 0)
        x_min, y_min, x_max, y_max = f_info.get_bounds(gn)
        x_extent.append(insertion_point + g_width)
        x_extent.append(insertion_point + x_max)
        insertion_point += g_width
        y_extent.append(y_min)
        y_extent.append(y_max)

    return min(x_extent), min(y_extent), max(x_extent), max(y_extent)


def draw_metrics_page(
    f_info, page_width, page_height, descender_global, normalize_upm=False
):

    upm = f_info.upm
    glyph_names = get_glyph_names(f_info)
    scale_factor = PT_SIZE / upm
    x_offset = MARGIN_L / scale_factor

    x_min, y_min, x_max, y_max = get_string_bounds(f_info, glyph_names)
    baseline = -descender_global / scale_factor + MARGIN / scale_factor
    db.newPage(page_width, page_height)

    line_labels = (
        ('OS/2 winAscent', f_info.winAscent),
        # winDescent is represented using a positive number, therefore * -1
        ('OS/2 winDescent', f_info.winDescent * -1),
        ('OS/2 typoAscender', f_info.ascender),
        ('OS/2 typoDescender', f_info.descender),

        ('baseline', 0,),
        ('x-height', f_info.xHeight),
        ('cap-height', f_info.capHeight),

        ('hhea ascender', f_info.hheaAscender),
        ('hhea descender', f_info.hheaDescender),
    )

    # sorting the labels according to their value
    line_labels = sorted(line_labels, key=lambda label: label[1])

    with db.savedState():
        db.scale(scale_factor)
        db.translate(x_offset, baseline)
        with db.savedState():
            # draw all the glyphs
            for glyph_name in glyph_names:
                if glyph_name not in f_info.glyph_set:
                    continue
                glyph = f_info.glyph_set[glyph_name]
                draw_glyph(glyph)
                db.translate(glyph.width, 0)

        with db.savedState():
            # no need to draw overlapping lines twice
            for y_value in set([value for _, value in line_labels]):
                db.stroke(0)
                db.strokeWidth(1)
                db.line((-4 / scale_factor, y_value), (x_max, y_value))

        with db.savedState():
            line_height = 10 / scale_factor
            # keep track of previous value for avoiding label overlap
            previous_label_baseline = -10000
            used_baselines = [previous_label_baseline]
            for line_index, (value_name, y_value) in enumerate(line_labels):
                db.font(FONT_MONO)
                db.fontSize(6 / scale_factor)
                db.fill(1, 0.186, 0.573)  # Strawberry
                v_offset = 10
                label_baseline = y_value + v_offset

                if label_baseline - previous_label_baseline <= line_height:
                    label_baseline += line_height
                    while label_baseline in used_baselines:
                        label_baseline += line_height
                    db.stroke(0)
                    db.strokeWidth(1)
                    db.line(
                        (-7 / scale_factor, label_baseline),
                        (-4 / scale_factor, y_value))
                    db.stroke(None)

                if 'winDescent' in value_name:
                    label_value = y_value * -1
                else:
                    label_value = y_value
                if normalize_upm and f_info.upm != 1000:
                    conversion_factor = 1000 / f_info.upm
                    label_value_conv = f'{label_value * conversion_factor:.0f}'
                    label = f'{value_name}: {label_value} ({label_value_conv})'
                else:
                    label = f'{value_name}: {label_value}'
                db.text(
                    label,
                    (-8 / scale_factor, label_baseline),
                    align='right')
                previous_label_baseline = label_baseline
                used_baselines.append(previous_label_baseline)

            # draw em-box
            db.stroke(0)
            db.strokeWidth(1)
            box_top = f_info.descender + f_info.upm
            db.line((0, f_info.descender), (0, box_top))
            db.line((0, box_top), (f_info.upm, box_top))
            db.line((f_info.upm, f_info.descender), (f_info.upm, box_top))
            db.stroke(None)

            # font name below
            db.text(
                f_info.ps_name,
                (MARGIN_L, 0 - line_height),
                align='left')


def report_metrics(fi, args):

    print('{:20s} {:>3d} 0 {:>3d} {:>3d} {:>3d}'.format(
        fi.styleName,
        fi.descender,
        fi.xHeight,
        fi.capHeight,
        fi.ascender))

    extremes = args.extremes
    if extremes > 1:
        print(f'{"":20s} lo {extremes}: {" ".join(fi.g_ymin)}')
        print(f'{"":20s} hi {extremes}: {" ".join(fi.g_ymax)}')


def finish_drawing(doc_name):
    output_path = Path(
        f'~/Desktop/vertical metrics {doc_name}.pdf').expanduser()
    db.saveImage(output_path)
    print('saved PDF to', output_path)
    subprocess.call(['open', output_path])
    db.endDrawing()


def get_global_metrics(fi_objects):
    '''
    measure all the FontInfo objects to see which one is the widest and
    tallest, from there deduce the dimensions of the page, and a global
    baseline
    '''
    string_heights = []
    descenders = []
    x_max_values = []
    for fi in fi_objects:
        glyph_names = get_glyph_names(fi)
        upm = fi.upm
        scale_factor = PT_SIZE / upm

        x_min, y_min, x_max, y_max = get_string_bounds(fi, glyph_names)
        x_max_values.append(x_max * scale_factor)
        string_height = sum([abs(y_min), y_max])
        string_heights.append(string_height * scale_factor)
        descender = min(fi.descender, fi.hheaDescender, -fi.winDescent)
        descenders.append(descender * scale_factor)

    x_max = max(x_max_values)
    descender = min(descenders)
    string_height = max(string_heights)

    page_width = x_max + MARGIN_L + MARGIN
    page_height = string_height + 4 * MARGIN
    return page_width, page_height, descender


def main():
    if IN_UI:
        file_or_folder = getFileOrFolder(allowsMultipleSelection=False)
        input_dir = str(file_or_folder[0])
        # would like to get # extremes and sample string here somehow...
        args = get_args([input_dir])

    else:
        args = get_args()

    font_paths = []
    for item in args.input:
        # could be individual fonts or folder of fonts.
        ip = Path(item)
        fonts = get_font_paths(ip)
        # sort them one-by-one
        font_paths.extend(
            fontSorter.sort_fonts(fonts, alternate_italics=False))

    if font_paths:
        fi_objects = [FontInfo(fp, args) for fp in font_paths]
        page_width, page_height, descender_gl = get_global_metrics(fi_objects)
        for fi in fi_objects:
            report_metrics(fi, args)
            draw_metrics_page(
                fi, page_width, page_height, descender_gl, args.normalize_upm)

        if args.output_file_name:
            doc_name = args.output_file_name
        else:
            name_overlap = get_name_overlap(
                [get_ps_name(f) for f in font_paths])

            if name_overlap and len(name_overlap) > 3:
                doc_name = name_overlap
            else:
                doc_name = get_path_overlap(font_paths)
            print(doc_name)

        if not IN_UI:
            finish_drawing(doc_name)
    else:
        print('no fonts found')


if __name__ == '__main__':
    main()
