# Copyright 2025 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Proofing tool for overlaying releated fonts on top of each other.
Some smartness is used to make sure fonts end up on the same baseline.

To-Do:
- make font pairing smarter
- allow overlaying static and VF

Input (pick one):
* folder(s) containing font files
* individual font files

'''

from fontTools.ttLib import TTFont
from pathlib import Path
from random import choice

import drawBot as db
import argparse
import math
import subprocess

from .proofing_helpers import fontSorter
from .proofing_helpers.fonts import make_temp_font
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.names import get_ps_name, get_unique_name


def get_args(default_args=None):

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        'ff_a',
        help='font or folder a')

    parser.add_argument(
        'ff_b',
        help='font or folder b')

    parser.add_argument(
        '-p', '--pt_size',
        default=16,
        type=int,
        help='point size')

    return parser.parse_args(default_args)


def get_text(length=2000):

    content_dir = Path(__file__).parent / '_content'
    with open(content_dir / 'moby_dick.txt', 'r', encoding='utf-8') as blob:
        lines = blob.read().splitlines()

    txt = ''
    while len(txt) < length:
        txt += choice(lines) + ' '

    return txt


def footer(name, color):
    fs = db.FormattedString(
        name,
        font=FONT_MONO,
        fontSize=10,
        fill=color,
    )
    return fs


def footer_vs(name_a, name_b, color_a, color_b):
    fs_color_a = footer(name_a, color_a)
    fs_black = footer(' vs ', 0)
    fs_color_b = footer(name_b, color_b)
    return fs_color_a + fs_black + fs_color_b


def calc_baseline_offset(f_a, f_b):
    '''
    unreliable. not used.
    '''
    upm_a = f_a['head'].unitsPerEm
    upm_b = f_b['head'].unitsPerEm

    fs_sel_a = f"{f_a['OS/2'].fsSelection:016b}"
    fs_sel_b = f"{f_b['OS/2'].fsSelection:016b}"

    use_typo_metrics_a = fs_sel_a[-7]
    use_typo_metrics_b = fs_sel_b[-7]

    if use_typo_metrics_a:
        asc_a = f_a['OS/2'].sTypoAscender
    else:
        asc_a = f_a['hhea'].ascender

    if use_typo_metrics_b:
        asc_b = f_b['OS/2'].sTypoAscender
    else:
        asc_b = f_b['hhea'].ascender

    asc_a = f_a['hhea'].ascender
    asc_b = f_b['hhea'].ascender

    norm_asc_a = asc_a / upm_a * 1000
    norm_asc_b = asc_b / upm_b * 1000

    get_caps_y_origin = norm_asc_b - norm_asc_a
    return get_caps_y_origin


def make_page(txt, font_a, font_b, color_a, color_b, pt_size):
    '''
    single page:
    font_a and font_b overlaid, setting the same text.
    '''
    margin = 20
    line_height = pt_size * 1.4

    db.newPage('A4')
    db.blendMode('multiply')

    f_a = TTFont(font_a)
    f_b = TTFont(font_b)

    uname_a = get_unique_name(font_a)
    uname_b = get_unique_name(font_b)

    content = db.FormattedString(
        txt, font=font_a, fontSize=pt_size, fill=color_a)

    baseline_offset_a = get_baseline_offset(font_a, pt_size)
    baseline_offset_b = get_baseline_offset(font_b, pt_size)
    offset_difference = baseline_offset_b - baseline_offset_a

    y = db.height() - margin
    num_lines = math.floor((db.height() - 3 * margin) / line_height)

    for i in range(num_lines):
        y -= line_height
        text_box_bounds = (
            margin, y, db.width() - 2 * margin, line_height)

        with db.savedState():
            db.translate(0, -offset_difference)
            db.textBox(
                # draw the background text
                db.FormattedString(
                    str(content), font=font_b,
                    fontSize=pt_size, fill=color_b,), text_box_bounds)

        # draw the foreground text
        content = db.textBox(content, text_box_bounds)

    db.text(footer_vs(uname_a, uname_b, color_a, color_b), (margin, margin))


def get_caps_y_origin(font, pt_size):
    '''
    Return the bottom y coordinate of the bounding box of H.
    For most fonts, this should be 0, but a shaded font may be negative.
    '''
    bp = db.BezierPath()
    bp.text('H', font=font, fontSize=pt_size)
    return bp.bounds()[1]


def get_baseline_offset(font, pt_size):
    '''
    Return the offset of the first baseline in respect to
    the top of a DrawBot textBox.

    I tried to calculate this for point size 1000 and scale later,
    but it seems like the scaling makes the result inaccurate.

    Also, just using the hhea ascender does not seem to work.
    '''
    width = height = 2000
    text_area = 0, 0, width, height
    bp = db.BezierPath()
    sample = db.FormattedString('H', font=font, fontSize=pt_size)
    bp.textBox(sample, text_area)
    bottom_bounds = bp.bounds()[1]
    baseline_zero_offset = get_caps_y_origin(font, pt_size)
    baseline_offset = bottom_bounds - height - baseline_zero_offset

    return baseline_offset


def make_pages(txt, fonts, pt_size):
    '''
    three pages, all setting the same text:
    font_a
    font_b
    font_a + font_b (overlaid)
    '''
    font_a, font_b = fonts

    black = (0)
    color_a = (0, 0, 1, 1)
    color_b = (1, 0, 0, 1)

    make_page(txt, font_a, font_b, black, None, pt_size)
    make_page(txt, font_a, font_b, None, black, pt_size)
    make_page(txt, font_a, font_b, color_a, color_b, pt_size)


def collect_fonts(paths):
    '''
    brittle. only seems to be possible to compare across versions
    of the same family.
    '''
    fonts_a = paths[0].rglob('*.[ot]tf')
    fonts_b = paths[1].rglob('*.[ot]tf')

    fonts_a_sorted = fontSorter.sort_fonts(list(fonts_a))
    fonts_sorted = {font.name: [font] for font in fonts_a_sorted}
    for font in fonts_b:
        if font.name in fonts_sorted.keys():
            fonts_sorted[font.name].append(font)

    font_pairs = [pair for pair in fonts_sorted.values() if len(pair) == 2]
    return font_pairs


def collect_fonts_os2(paths):
    '''
    brittle. only works reliably if folders have same amount of fonts.
    '''
    fonts_a = paths[0].rglob('*.[ot]tf')
    fonts_b = paths[1].rglob('*.[ot]tf')

    fonts_a_sorted = sorted(
        fonts_a, key=lambda x:
        (TTFont(x)['OS/2'].usWidthClass, TTFont(x)['OS/2'].usWeightClass))
    fonts_b_sorted = sorted(
        fonts_b, key=lambda x:
        (TTFont(x)['OS/2'].usWidthClass, TTFont(x)['OS/2'].usWeightClass))

    font_pairs = zip(fonts_a_sorted, fonts_b_sorted)
    return font_pairs


def get_style_name(font_path):
    f = TTFont(font_path)
    style_name = f['name'].getDebugName(17)
    if not style_name:
        style_name = f['name'].getDebugName(2)
    return style_name


def collect_font_pairs(paths):
    '''
    Find font pairs sharing style name.
    May drop fonts if a style name only exists on one side
    '''
    fonts_a = paths[0].rglob('*.[ot]tf')
    fonts_b = list(paths[1].rglob('*.[ot]tf'))

    fonts_a_sorted = fontSorter.sort_fonts(list(fonts_a))
    style_names_a = [get_style_name(f) for f in fonts_a_sorted]
    style_names_b = [get_style_name(f) for f in fonts_b]

    font_pairs = {}
    for style_name in style_names_a:
        if style_name in style_names_b:
            index_a = style_names_a.index(style_name)
            index_b = style_names_b.index(style_name)
            font_a = fonts_a_sorted[index_a]
            font_b = fonts_b[index_b]
            font_pairs[style_name] = (font_a, font_b)

    return font_pairs


def main():
    args = get_args()
    paths = [Path(i) for i in [args.ff_a, args.ff_b]]
    txt = get_text()

    if all([p.is_dir() for p in paths]):
        font_pairs = collect_font_pairs(paths)
        fonts = font_pairs.values()
        color_a = (0, 0, 1, 1)
        color_b = (1, 0, 0, 1)

        print('font pairs found:')
        for style_name, font_pair in font_pairs.items():
            font_a, font_b = font_pair
            print(f'{font_a.name}')
            print(f'{font_b.name}')
            print()

        pdf_name = f'overlay {" vs ".join(p.name for p in paths)}.pdf'

        for font_pair in fonts:
            temp_fonts = [
                make_temp_font(fi, f) for fi, f in enumerate(font_pair)]
            tf_a, tf_b = temp_fonts
            make_page(txt, tf_a, tf_b, color_a, color_b, args.pt_size)

    elif all([p.is_file() for p in paths]):
        fonts = paths
        ps_names = [get_ps_name(f) for f in fonts]
        if len(set(ps_names)) == 1:
            pdf_name = f'overlay {ps_names[0]}.pdf'
        else:
            pdf_name = f'overlay {" vs ".join(ps_names)}.pdf'

        ps_names = [get_ps_name(f) for f in fonts]
        temp_fonts = [
            make_temp_font(fi, f) for fi, f in enumerate(fonts)]
        make_pages(txt, temp_fonts, args.pt_size)

    else:
        fonts = []
        paths_exist = True
        for p in paths:
            if not p.exists():
                paths_exist = False
                print(p, 'does not exist')
        if paths_exist:
            print('cannot compare across paths and files')

    if fonts:
        pdf_path = Path(f'~/Desktop/{pdf_name}').expanduser()
        db.saveImage(pdf_path)
        subprocess.Popen(['open', pdf_path])
    else:
        print('could not find any fonts')


if __name__ == '__main__':
    main()
