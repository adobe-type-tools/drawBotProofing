from fontTools.ttLib import TTFont
from pathlib import Path
from .proofing_helpers.files import make_temp_font
from .proofing_helpers.globals import FONT_MONO
from random import choice

import drawBot as db
import argparse
import subprocess


def get_args(default_args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'ff_a',
        help='font or folder a')

    parser.add_argument(
        'ff_b',
        help='font or folder b')

    return parser.parse_args(default_args)


def get_text(length=2000):
    txt_file_english = (
        '/Users/fg/Dropbox/scripts/text/languages/english.txt')
    with open(txt_file_english, 'r', encoding='utf-8') as blob:
        lines = blob.read().splitlines()

    txt = ''
    while len(txt) < length:
        txt += choice(lines) + ' '

    return txt


def make_comparison_page(txt, font_a, font_b):
    margin = 20
    color_a = (0, 0, 1, 1)
    color_b = (1, 0, 0, 1)
    db.newPage('A4')
    db.blendMode('multiply')
    uname_a = TTFont(font_a)['name'].getDebugName(3)
    uname_b = TTFont(font_b)['name'].getDebugName(3)

    # text VF
    fs_var = db.FormattedString(
        txt,
        font=font_a,
        fontSize=16,
        fill=color_a,
    )
    # text static
    fs_static = db.FormattedString(
        txt,
        font=font_b,
        fontSize=16,
        fill=color_b,
    )
    text_box_bounds = (
        margin, 2 * margin, db.width() - 2 * margin, db.height() - 3 * margin)
    db.textBox(fs_var, text_box_bounds)
    db.textBox(fs_static, text_box_bounds)

    # description at bottom
    fs_vf = db.FormattedString(
        f'{uname_a}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_a,
    )
    fs_vs = db.FormattedString(
        ' vs ',
        font=FONT_MONO,
        fontSize=10,
        fill=0,
    )
    fs_static = db.FormattedString(
        f'{uname_b}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_b,
    )
    fonts_compared = fs_vf + fs_vs + fs_static
    db.text(fonts_compared, (margin, margin))


def get_fs(font, txt, color):
    fs = db.FormattedString(
        txt,
        font=font,
        fontSize=16,
        fill=color,
    )
    return fs


def get_ps_name(font):
    return TTFont(font)['name'].getDebugName(6)


def make_comparison_pages(txt, fonts):
    font_a, font_b = fonts
    margin = 20
    color_a = (0, 0, 1, 1)
    color_b = (1, 0, 0, 1)
    color_black = (0, 0, 0, 1)

    db.newPage('A4')
    uname_a = TTFont(font_a)['name'].getDebugName(3)
    uname_b = TTFont(font_b)['name'].getDebugName(3)

    text_box_bounds = (
        margin, 2 * margin, db.width() - 2 * margin, db.height() - 3 * margin)

    fs_page_1 = get_fs(font_a, txt, color_black)
    # description at bottom
    footer_page_1 = db.FormattedString(
        f'{uname_a}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_black,
    )
    db.textBox(fs_page_1, text_box_bounds)
    db.text(footer_page_1, (margin, margin))

    db.newPage('A4')
    fs_page_2 = get_fs(font_b, txt, color_black)
    footer_page_2 = db.FormattedString(
        f'{uname_b}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_black,
    )
    db.textBox(fs_page_2, text_box_bounds)
    db.text(footer_page_2, (margin, margin))

    db.newPage('A4')
    db.blendMode('multiply')
    fs_color_a = get_fs(font_a, txt, color_a)
    fs_color_b = get_fs(font_b, txt, color_b)
    db.textBox(fs_color_a, text_box_bounds)
    db.textBox(fs_color_b, text_box_bounds)

    # description at bottom
    footer_color_a = db.FormattedString(
        f'{uname_a}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_a,
    )
    footer_color_black = db.FormattedString(
        ' vs ',
        font=FONT_MONO,
        fontSize=10,
        fill=0,
    )
    footer_color_b = db.FormattedString(
        f'{uname_b}',
        font=FONT_MONO,
        fontSize=10,
        fill=color_b,
    )
    footer_page_3 = footer_color_a + footer_color_black + footer_color_b
    db.text(footer_page_3, (margin, margin))


def collect_fonts(paths):
    from .proofing_helpers import fontSorter
    otfs_a = paths[0].rglob('*.otf')
    otfs_b = paths[1].rglob('*.otf')
    otfs_a_sorted = fontSorter.sort_fonts(list(otfs_a))

    otfs_sorted = {otf.name: [otf] for otf in otfs_a_sorted}
    for otf in otfs_b:
        if otf.name in otfs_sorted.keys():
            otfs_sorted[otf.name].append(otf)

    font_pairs = [pair for pair in otfs_sorted.values() if len(pair) == 2]
    return font_pairs


def main():
    """Main entry point for the overlay-font-proof command."""
    args = get_args()
    paths = [Path(i) for i in [args.ff_a, args.ff_b]]
    txt = get_text()

    if all([p.is_dir() for p in paths]):
        fonts = collect_fonts(paths)
        pdf_name = f'overlay_fonts {" vs ".join(p.name for p in paths)}.pdf'

        for font_pair in fonts:
            temp_fonts = [
                make_temp_font(fi, f) for fi, f in enumerate(font_pair)]
            make_comparison_page(txt, *temp_fonts)

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
        db.saveImage(pdf_name)
        subprocess.Popen(['open', pdf_name])


if __name__ == '__main__':
    main() 