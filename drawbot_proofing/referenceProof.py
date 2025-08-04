# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Create lines for a string of characters, set in all fonts that support it.
The choice of fonts is either all installed fonts (no argument), or all fonts
in a given folder tree. The font list can be filtered by supplying a regular
expression.

This proof helps solving the question:
“How do other fonts deal with this weird glyph?”

Slow.

'''

import argparse
import drawBot as db
import logging
import multiprocessing
import re
import subprocess
import CoreText

from fontTools import ttLib
from itertools import repeat
from pathlib import Path

from .proofing_helpers.globals import ADOBE_BLANK, FONT_MONO
from .proofing_helpers.names import get_overlap_index, get_ps_name

logger = logging.getLogger('fontTools')
logger.setLevel(level=logging.CRITICAL)
# otherwise a lot of irrelevant output:
# 1 extra bytes in post.stringData array


EXCLUDE_FONTS = [
    'LastResort',
    'AND-Regular',
    'AdobeBlank',
]


class FontFileInfo(object):
    def __init__(self, font_path, ps_name, font_number=0):
        self.path = font_path
        self.suffix = font_path.suffix
        self.ps_name = ps_name
        self.font_number = font_number


def get_installed_font_path(ps_name):
    ctFont = CoreText.CTFontDescriptorCreateWithNameAndSize(ps_name, 10)
    if ctFont is None:
        print(f'The font "{ps_name}" is not installed')
    else:
        url = CoreText.CTFontDescriptorCopyAttribute(
            ctFont, CoreText.kCTFontURLAttribute)
        font_path = url.path()
        return Path(font_path)


def path_for_ps_name(ps_name):
    if ps_name.startswith('.'):
        # don't even try to look at system UI fonts: they don't
        # work (sub to Times New Roman) and attempting to access
        # causes an ugly warning message to be emitted.
        pass
    font_path = get_installed_font_path(ps_name)
    return font_path


def filter_fonts_by_regex(fonts, regex):
    rex = re.compile(regex)
    filtered_names = list(
        filter(rex.match, [fo.ps_name for fo in fonts]))
    if filtered_names:
        font_objects = [fo for fo in fonts if fo.ps_name in filtered_names]
    else:
        print('No match for regular expression.')
        font_objects = []

    return font_objects


def get_ttc_styles(font_path):
    '''
    Return a dict of ttc font numbers to PS names
    '''
    ttc_styles = {}
    tt_collection = ttLib.TTCollection(font_path)
    for i, ttfont in enumerate(tt_collection.fonts):
        ps_name = ttfont['name'].names[6].toUnicode()
        ttc_styles[i] = ps_name
    return ttc_styles


def get_font_number_for_ps_name(font_path, ps_name):
    ttc_style_dict = get_ttc_styles(font_path)
    reversed_style_dict = {
        value: key for (key, value) in ttc_style_dict.items()}
    return reversed_style_dict.get(ps_name, 0)


def get_cmap(font_path, ttc_arg=0):
    '''
    get the cmap from a font.
    TTCs can be accessed via font number or PS name.
    '''
    if isinstance(ttc_arg, int):
        font_number = ttc_arg
        ttfont = ttLib.TTFont(font_path, fontNumber=font_number)
    else:
        ps_name = ttc_arg
        font_number = get_font_number_for_ps_name(font_path, ps_name)
        ttfont = ttLib.TTFont(font_path, fontNumber=font_number)

    try:
        return ttfont['cmap'].getBestCmap()
    except Exception:
        return {}


def supports_chars(ffi, chars):
    support = False
    cmap = get_cmap(ffi.path, ffi.font_number)

    if cmap and set([ord(char) for char in chars]) <= cmap.keys():
        support = True

    return ffi, support


def font_path_to_ffi(font_path):
    '''
    Return a list of one (otf/ttf) or multiple (ttc) font file info objects.
    '''
    ffi_objects = []
    if font_path.suffix.lower() == '.ttc':
        ttc_style_dict = get_ttc_styles(font_path)
        for font_number, ps_name in ttc_style_dict.items():
            ffi = FontFileInfo(font_path, ps_name, font_number)
            ffi_objects.append(ffi)
    else:
        ps_name = get_ps_name(font_path)
        if ps_name is None:
            ps_name = font_path.stem
        ffi = FontFileInfo(font_path, ps_name)
        ffi_objects.append(ffi)

    return ffi_objects


def get_available_fonts(args):
    '''
    Return a list of objects, which contain a font’s path, PS name,
    and a font number (if applicable).
    '''
    available_fonts = []
    if args.input_path:
        input_path = Path(args.input_path)
        if input_path.is_dir():  # find fonts in input_path
            font_paths = (
                list(input_path.rglob('*.otf')) +
                list(input_path.rglob('*.OTF')) +
                list(input_path.rglob('*.tt[fc]')) +
                list(input_path.rglob('*.TT[FC]')))

            for font_path in font_paths:
                if (
                    font_path.parent.name != 'AFE' and
                    # The AFE folder contains weird fonts w/o outlines
                    font_path.stem not in EXCLUDE_FONTS
                ):
                    available_fonts.extend(font_path_to_ffi(font_path))

        elif input_path.is_file():
            available_fonts.extend(font_path_to_ffi(input_path))
        else:
            print(f'{args.input_path} seems to be invalid.')

    else:  # use installed fonts
        installed_fonts = db.installedFonts()
        print(f'Processing {len(installed_fonts)} installed fonts...')

        with multiprocessing.Pool() as pool:
            try:
                font_paths = pool.map(path_for_ps_name, installed_fonts)
                # Filter out None values from failed font path lookups
                valid_font_paths = [fp for fp in font_paths if fp is not None]
                available_fonts = sum(
                    pool.map(font_path_to_ffi, valid_font_paths), [])
            except Exception as e:
                print(f'Error processing installed fonts: {e}')
                return []

    return available_fonts


def collect_font_objects(args):
    available_fonts = get_available_fonts(args)

    if args.regex:  # filtering by possible regex
        available_fonts = filter_fonts_by_regex(available_fonts, args.regex)

    # filtering for character support
    print(f'Checking character support for {len(available_fonts)} fonts...')
    with multiprocessing.Pool() as pool:
        try:
            support_map = pool.starmap(
                supports_chars, zip(available_fonts, repeat(args.chars)))
            filtered_fonts = [
                ffi for (ffi, support) in support_map if support is True]
            print(f'Found {len(filtered_fonts)} fonts supporting "{args.chars}"')
        except Exception as e:
            print(f'Error checking character support: {e}')
            return []

    # simple sorting by PS name -- this is imperfect but makes sense for
    # installed fonts, or when a deep folder tree is parsed.
    return sorted(
        filtered_fonts, key=lambda fo: (fo.ps_name, fo.font_number, fo.suffix))


def make_pdf_name(args):
    chars_safe = args.chars.replace('/', '_')  # remove slash from path

    if args.input_path:
        short_dir = Path(args.input_path).name
        pdf_name = f'comparisonProof {chars_safe} ({short_dir}).pdf'

    else:
        pdf_name = f'comparisonProof {chars_safe} (installed fonts).pdf'

    return pdf_name


def make_line(args, ffi):
    '''
    Create a FormattedString with a line of content, using a font indicated
    by ffi.path. A label with the PS name is added.
    '''
    fs = db.FormattedString(
        args.chars + ' ',
        font=ffi.path,
        fontSize=int(args.pt),
        fontNumber=ffi.font_number,
        fallbackFont=ADOBE_BLANK,
    )
    fs.append(
        ffi.ps_name,
        font=FONT_MONO,
        fontSize=10)
    return fs


def make_document(args, formatted_strings):
    margin = int(args.pt)
    line_number = 0
    line_height = int(args.pt) * 1.2
    pagespec = f'{args.pagesize}{"Landscape" if args.landscape else ""}'

    db.newDrawing()
    db.newPage(pagespec)
    for fs in formatted_strings:
        line_number += 1
        current_baseline = (db.height() - margin - line_height * line_number)
        db.text(fs, (margin, current_baseline))

        if line_number * line_height + 4 * margin >= db.height():
            db.newPage(pagespec)
            line_number = 0

    pdf_name = make_pdf_name(args)
    output_path = Path(f'~/Desktop/{pdf_name}').expanduser()
    db.saveImage(output_path)
    db.endDrawing()
    return output_path


def get_options(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'chars',
        metavar='',
        nargs='?',
        action='store',
        default='abc123',
        help='characters to sample')

    parser.add_argument(
        '-r', '--regex',
        action='store',
        metavar='REGEX',
        type=str,
        help='regular expression to filter font list')

    parser.add_argument(
        '--pt',
        action='store',
        metavar='POINTS',
        default=30,
        help='point size')

    parser.add_argument(
        '--headless',
        default=False,
        action='store_true',
        help='do not open result PDF after generating')

    parser.add_argument(
        '-d', '--input_path',
        action='store',
        metavar='FOLDER',
        help='folder to crawl (default is using all installed fonts)')

    parser.add_argument(
        '--pagesize',
        choices=[size for size in db.sizes() if "Landscape" not in size],
        default="Letter",
        help='page size')

    parser.add_argument(
        '--landscape',
        default=False,
        action='store_true',
        help='landscape orientation (default is portrait)')

    return parser.parse_args(args)


def main(test_args=None):
    args = get_options(test_args)
    font_objects = collect_font_objects(args)

    all_paths = [str(ffi.path) for ffi in font_objects]
    overlap_index = get_overlap_index(all_paths)
    formatted_strings = []

    used_ps_names = []
    for ffi in font_objects:
        if ffi.ps_name not in used_ps_names:
            formatted_strings.append(make_line(args, ffi))
            used_ps_names.append(ffi.ps_name)
            print(str(ffi.path)[overlap_index:])

    if formatted_strings:
        output_path = make_document(args, formatted_strings)

    if not args.headless:
        if output_path.exists():
            print(output_path)
            subprocess.call(['open', output_path])
        else:
            print('No fonts found.')


if __name__ == '__main__':
    main()
