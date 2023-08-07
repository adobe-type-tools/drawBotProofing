# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates simple view which illustrates all vertical metrics
set in the font metadata. Additionally, tallest and lowest glyphs are shown.

Using the -n option, the number of extreme glyphs can be increased.

Input: font file

'''

import argparse
from pathlib import Path
import subprocess
import sys

import drawBot as db
from fontTools.pens.boundsPen import BoundsPen
from fontTools import ttLib

from proofing_helpers.drawing import draw_glyph
from proofing_helpers.files import get_font_paths
from proofing_helpers.globals import FONT_MONO
from proofing_helpers.fontSorter import sort_fonts
from proofing_helpers.names import get_ps_name, get_name_overlap

IN_UI = 'drawBot.ui' in sys.modules

if IN_UI:
    from vanilla.dialogs import getFileOrFolder  # noqa: F401

PT_SIZE = 200
MARGIN = 20
MARGIN_L = 6 * MARGIN


def get_glyph_names(fi):
    # Some standard glyphs defining basic metrics,
    # as well as tallest and lowest glyphs.
    glyph_names = list(fi.sample_string)
    glyph_names += fi.g_ymin
    glyph_names += fi.g_ymax
    return glyph_names


def get_options(args=None, description=__doc__):
    parser = argparse.ArgumentParser(
        description=description)

    parser.add_argument(
        'input_dir',
        action='store',
        metavar='FOLDER',
        help='folder to crawl')

    parser.add_argument(
        '-o', '--output_file_name',
        action='store',
        metavar='PDF',
        help='output file name')

    parser.add_argument(
        '-n', '--num_extremes',
        type=int,
        default=1,
        help='number of extreme glyphs')

    parser.add_argument(
        '-s', '--sample_string',
        type=str,
        default='Hxbpg',
        help='sample string')

    return parser.parse_args(args)


class FontInfo(object):

    def __init__(self, font_path, args):
        self.path = font_path.resolve()
        self.ttf = ttLib.TTFont(self.path)
        self.glyph_set = self.ttf.getGlyphSet()
        self.ascender = 0
        self.descender = 0
        self.xHeight = 0
        self.capHeight = 0
        self.cap_H_width = 0
        self.sample_string = args.sample_string
        self.extract_vertical_metrics()
        self.extract_extreme_n_glyphs(n=args.num_extremes)
        self.extract_names()
        self.extract_widths()
        self.extract_upm()
        self.parse_cmap()
        self.extract_cap_H_width()
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

    def parse_cmap(self):
        cmap_table = self.ttf['cmap']
        self.char_map = cmap_table.getBestCmap()
        self.reverse_char_map = {
            gname: chr(c_index) for c_index, gname in self.char_map.items()
        }

    def extract_cap_H_width(self):
        # do not assume the glyph name for 'H' to be 'H'
        cap_H_gname = self.char_map.get(ord('H'), '.notdef')
        self.cap_H_width = self.advance_widths.get(cap_H_gname)


def draw_metrics_page(f_info, page_width=5000):
    upm = f_info.upm
    glyph_names = get_glyph_names(f_info)
    scale_factor = PT_SIZE / upm
    x_offset = MARGIN_L / scale_factor
    font_height = f_info.winAscent + f_info.winDescent
    page_height = font_height * 1.4 * scale_factor
    db.newPage(page_width, page_height)
    baseline = db.height() / 3 / scale_factor

    line_labels = (
        ('os/2 winAscent', f_info.winAscent),
        ('os/2 winDescent', f_info.winDescent * -1),
        # winDescent is represented using a positive number
        ('os/2 typoAscender', f_info.ascender),
        ('os/2 typoDescender', f_info.descender),

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

        string_width = sum([
            # fallback value 0 is for whenever a glyph is not supported
            f_info.advance_widths.get(glyph_name, 0)
            for glyph_name in glyph_names])

        with db.savedState():
            # no need to draw overlapping lines twice
            for y_value in set([value for _, value in line_labels]):
                db.stroke(0)
                db.strokeWidth(1)
                db.line((-4 / scale_factor, y_value), (string_width, y_value))

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
                    label_value = str(y_value * -1)
                else:
                    label_value = str(y_value)
                db.text(
                    f'{value_name}: {label_value}',
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


def process_font_path(font_path, args):
    fi = FontInfo(font_path, args)
    glyph_names = get_glyph_names(fi)
    page_width = sum(
        [fi.advance_widths.get(gn, 0) * PT_SIZE / fi.upm for gn in glyph_names]
    ) + MARGIN_L + MARGIN

    print('{:20s} {:>3d} 0 {:>3d} {:>3d} {:>3d}'.format(
        fi.styleName,
        fi.descender,
        fi.xHeight,
        fi.capHeight,
        fi.ascender))

    if args.num_extremes > 1:
        print(f'{"":20s} lo {args.num_extremes}: {" ".join(fi.g_ymin)}')
        print(f'{"":20s} hi {args.num_extremes}: {" ".join(fi.g_ymax)}')

    draw_metrics_page(fi, page_width)


def finish_drawing(doc_name):
    output_path = Path(
        f'~/Desktop/vertical metrics {doc_name}.pdf').expanduser()
    db.saveImage(output_path)
    print('saved PDF to', output_path)
    subprocess.call(['open', output_path])
    db.endDrawing()


if __name__ == '__main__':
    if IN_UI:
        file_or_folder = getFileOrFolder(allowsMultipleSelection=False)
        input_dir = str(file_or_folder[0])
        # would like to get # extremes and sample string here somehow...
        args = get_options([input_dir])

    else:
        args = get_options()

    font_paths = get_font_paths(args.input_dir)
    sorted_font_paths = sort_fonts(font_paths)

    for font_path in sorted_font_paths:
        process_font_path(font_path, args)

    if args.output_file_name:
        doc_name = args.output_file_name
    else:
        doc_name = get_name_overlap([p.name for p in sorted_font_paths])

    if not IN_UI:
        finish_drawing(doc_name)
