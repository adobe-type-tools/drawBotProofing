from fontTools.ttLib import TTFont
from pathlib import Path
from random import choice

import drawBot as db
import argparse
import subprocess

from .proofing_helpers import fontSorter
from .proofing_helpers.files import make_temp_font
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO


def get_args(default_args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )
    parser.add_argument(
        'ff_a',
        help='font or folder a')

    parser.add_argument(
        'ff_b',
        help='font or folder b')

    return parser.parse_args(default_args)


def get_text(length=2000):

    content_dir = Path(__file__).parent / '_content'
    with open(content_dir / 'moby_dick.txt', 'r', encoding='utf-8') as blob:
        lines = blob.read().splitlines()

    txt = ''
    while len(txt) < length:
        txt += choice(lines) + ' '

    return txt


def get_ps_name(font):
    return TTFont(font)['name'].getDebugName(6)


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


def content(font, txt, color):
    fs = db.FormattedString(
        txt,
        font=font,
        fontSize=16,
        fill=color,
    )
    return fs


def make_overlay_page(txt, font_a, font_b):
    '''
    single page:
    font_a and font_b overlaid, setting the same text.
    '''
    margin = 20
    color_a = (0, 0, 1, 1)
    color_b = (1, 0, 0, 1)

    db.newPage('A4')
    text_box_bounds = (
        margin, 2 * margin, db.width() - 2 * margin, db.height() - 3 * margin)

    db.blendMode('multiply')
    uname_a = TTFont(font_a)['name'].getDebugName(3)
    uname_b = TTFont(font_b)['name'].getDebugName(3)

    content_a = content(font_a, txt, color_a)
    content_b = content(font_b, txt, color_b)

    db.textBox(content_a, text_box_bounds)
    db.textBox(content_b, text_box_bounds)
    db.text(footer_vs(uname_a, uname_b, color_a, color_b), (margin, margin))


def make_comparison_pages(txt, fonts):
    '''
    three pages, all setting the same text:
    font_a
    font_b
    font_a + font_b (overlaid)
    '''
    font_a, font_b = fonts
    margin = 20

    uname_a = TTFont(font_a)['name'].getDebugName(3)
    uname_b = TTFont(font_b)['name'].getDebugName(3)

    db.newPage('A4')

    text_box_bounds = (
        margin, 2 * margin, db.width() - 2 * margin, db.height() - 3 * margin)

    content_page_1 = content(font_a, txt, 0)
    footer_page_1 = footer(uname_a, 0)
    db.textBox(content_page_1, text_box_bounds)
    db.text(footer_page_1, (margin, margin))

    db.newPage('A4')
    content_page_2 = content(font_b, txt, 0)
    footer_page_2 = footer(uname_b, 0)
    db.textBox(content_page_2, text_box_bounds)
    db.text(footer_page_2, (margin, margin))

    make_overlay_page(txt, font_a, font_b)


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
    may drop fonts if a style name only exists on one side
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

        print('font pairs found:')
        for style_name, font_pair in font_pairs.items():
            font_a, font_b = font_pair
            print(style_name)
            print(f'\t{font_a.name}')
            print(f'\t{font_b.name}')
            print()

        pdf_name = f'overlay_fonts {" vs ".join(p.name for p in paths)}.pdf'

        for font_pair in fonts:
            temp_fonts = [
                make_temp_font(fi, f) for fi, f in enumerate(font_pair)]
            make_overlay_page(txt, *temp_fonts)

    elif all([p.is_file() for p in paths]):
        fonts = paths
        ps_names = [get_ps_name(f) for f in fonts]
        if len(set(ps_names)) == 1:
            pdf_name = f'overlay_fonts {ps_names[0]}.pdf'
        else:
            pdf_name = f'overlay_fonts {" vs ".join(ps_names)}.pdf'

        ps_names = [get_ps_name(f) for f in fonts]
        temp_fonts = [
            make_temp_font(fi, f) for fi, f in enumerate(fonts)]
        make_comparison_pages(txt, temp_fonts)

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
