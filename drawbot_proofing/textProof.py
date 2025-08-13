# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Create example paragraphs corresponding to a given character set.

Default mode is creating single-page PDF with a random subset of the requested
charset. Optionally, a full charset can be consumed systematically, to show
as many characters as possible.
The alternative mode is using a text file as input, to achieve more predictable
(and comparable) output. In text-mode, the output is limited to a single
page (no matter how long the text file may be).

Known bug:
Line spacing may become inconsistent if a character set beyond the font’s
character support is requested (this is a macOS limitation caused by the
vertical metrics in a given fallback font).

Input:
* font file(s), or folder(s) containing font files

Optional input:
* choice of text file (`-t`) or charset name (`-c`)
* secondary font(s) (`-s`) (for mixing Roman/Italic, for example)

'''

import re
import sys

import argparse
import itertools
import random
import subprocess
import textwrap

import drawBot as db
from fontTools.ttLib import TTFont
from pathlib import Path

from .proofing_helpers import fontSorter
from .proofing_helpers import charsets as cs
from .proofing_helpers.globals import FONT_MONO, ADOBE_BLANK, ADOBE_NOTDEF
from .proofing_helpers.fonts import get_default_instance
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.helpers import uni_names
from .proofing_helpers.files import (
    get_font_paths, chain_charset_texts, read_text_file, make_temp_font)
from .proofing_helpers.stamps import timestamp


DOC_SIZE = 'Letter'
MARGIN = 12


class TextContainer(object):
    def __init__(self, text, italic=False, paragraph=False):
        self.text = text.strip()
        self.italic = italic
        self.paragraph = paragraph


def get_options():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )

    charset_choices = [name for name in dir(cs) if not name.startswith('_')]

    parser.add_argument(
        # '-f', '--fonts',
        'fonts',
        nargs='+',
        # required=True,
        metavar='FONT',
        help='font file or folder')

    group = parser.add_mutually_exclusive_group(required=False)

    # either choose a charset, or reproduce a text file
    group.add_argument(
        '-c', '--charset',
        action='store',
        default='al3',
        choices=charset_choices,
        type=str.lower,
        help='character set (for randomized text)')

    group.add_argument(
        '-t', '--text_file',
        action='store',
        metavar='TXT',
        help='text file (for predictable text)')
    # ----------- end of group

    parser.add_argument(
        '--filter',
        action='store',
        metavar='ABC',
        help='required characters')

    parser.add_argument(
        '--capitalize',
        action='store_true',
        default=False,
        help='capitalize output')

    parser.add_argument(
        '-p', '--pt_size',
        action='store',
        default=10,
        type=int,
        help='point size for sample')

    parser.add_argument(
        '-k', '--kerning_off',
        default=False,
        action='store_true',
        help='switch off kerning')

    parser.add_argument(
        '-a', '--full',
        action='store_true',
        help='consume whole character set')

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='report information about the characters used')

    parser.add_argument(
        '-s', '--secondary_fonts',
        nargs='+',
        metavar='FONT',
        default=[],
        help='secondary font file or folder')

    return parser.parse_args()


def merge_chunks(chunks, chunk_length=5):
    output = []
    appended = 0
    for chunk in chunks:
        if len(chunk) < chunk_length and appended > 0:
            output[appended - 1] += chunk
        else:
            output.append(chunk)
            appended += 1
    return output


def consume_charset(content_list, charset):
    '''
    Keep collecting paragraphs until every character of a given charset has
    been used.
    '''
    character = random.choice(list(charset))
    found_paragraphs = [p for p in content_list if character in p]
    if found_paragraphs:
        paragraph_pick = random.choice(found_paragraphs)
        remaining_charset = set(charset) - set(paragraph_pick)
    else:
        paragraph_pick, remaining_charset = consume_charset(
            content_list, charset)

    return paragraph_pick, remaining_charset


def message_with_charset(message, characters, wrap_length=70):
    chars = '\n'.join(textwrap.wrap(' '.join(sorted(characters)), wrap_length))
    print(f'{message} ({len(characters)}):\n{chars}\n')


def analyze_missing(content_pick, content_list, charset_name):
    '''
    Report stats about the chosen character set, which characters were
    used in the sample, etc.
    '''
    abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    chars = getattr(cs, charset_name)
    missing_abc = set(abc) - set(''.join(content_pick))
    missing_charset = set(chars) - set(''.join(content_pick))
    missing_cset_source = set(chars) - set(''.join(content_list))

    message_with_charset(charset_name.upper(), chars)

    if missing_abc:
        message_with_charset('missing alphabetic characters', missing_abc)

    if missing_charset:
        message_with_charset(
            f'missing {charset_name.upper()} characters in output text',
            missing_charset)

    if missing_cset_source:
        print(
            f'missing {charset_name.upper()} characters '
            f'in source text ({len(missing_cset_source)}):')
        print('\n'.join(uni_names(missing_cset_source)))


def make_proof(content, fonts_a, fonts_b, args, output_name):

    db.newDrawing()

    # make temporary fonts
    temp_fonts = {}
    for i, font in enumerate(fonts_a + fonts_b):
        temp_fonts[font] = make_temp_font(i, font)

    fea_dict = {
        'liga': True,
        # 'onum': True,
        # 'pnum': True,
        # 'tnum': True,
    }
    if args.kerning_off:
        fea_dict['kern'] = False

    if fonts_b:
        font_pairs = list(itertools.product(fonts_a, fonts_b))
        num_combinations = len(font_pairs)
        if num_combinations > 20:
            print(f'proofing {num_combinations} font combinations …')
        for font_a, font_b in font_pairs:
            fs = make_page_content(
                content, font_a, font_b, args.pt_size, fea_dict, temp_fonts)
            make_page(fs, font_a, font_b, args)
    else:
        for font in fonts_a:
            fs = make_page_content(
                content, font, None, args.pt_size, fea_dict, temp_fonts)
            make_page(fs, font, None, args)

    pdf_path = Path(f'~/Desktop/{output_name}.pdf')
    db.saveImage(pdf_path)

    db.endDrawing()
    print(f'saved to {pdf_path}')
    subprocess.call(['open', pdf_path.expanduser()])


def make_page_content(content, font_a, font_b, pt_size, fea_dict, temp_fonts):
    '''
    Page-filling FormattedString, which uses different kinds of fonts and
    some natural-looking paragraphs.
    '''
    fs = db.FormattedString(
        fontSize=pt_size,
        fallbackFont=ADOBE_BLANK,
        openTypeFeatures=fea_dict,
    )

    for text_item in content:
        if text_item.italic and font_b:
            tmp_font_b = temp_fonts[font_b]
            instance = get_default_instance(tmp_font_b)
            fs.append(
                text_item.text,
                font=tmp_font_b,
                fallbackFont=ADOBE_NOTDEF,
                fontVariations=instance
            )
        else:
            tmp_font_a = temp_fonts[font_a]
            instance = get_default_instance(tmp_font_a)
            fs.append(
                text_item.text,
                font=tmp_font_a,
                fallbackFont=ADOBE_NOTDEF,
                fontVariations=instance
            )

        if text_item.paragraph:
            fs.append('\n\n')
        else:
            fs.append(' ')
    return fs


def make_page(fs, font_a, font_b, args):

    db.newPage(DOC_SIZE)
    if args.charset == 'abc':
        # We do not want any non-ABC characters (such as the hyphen)
        # in an ABC-only proof
        db.hyphenation(False)
    else:
        db.hyphenation(True)

    footer_label = f'{timestamp(readable=True)} | {font_a.name}'
    if font_b:
        footer_label += f' + {font_b.name}'
    footer_label += f' | {args.pt_size} pt'
    if args.kerning_off:
        footer_label += ' (no kerning)'

    fs_footer = db.FormattedString(
        footer_label,
        font=FONT_MONO,
        fontSize=6,
    )

    fs_overflow = db.textBox(
        fs, (
            6 * MARGIN, 5 * MARGIN,
            db.width() - 9 * MARGIN, db.height() - 7 * MARGIN
        ))
    db.textBox(fs_footer, (6 * MARGIN, 0, db.width(), 3 * MARGIN))

    if fs_overflow and args.full:
        make_page(
            fs_overflow, font_a, font_b, args)

    else:
        return fs_overflow


def format_content(content_list, len_limit=None, capitalize=False):
    total_length = 0
    formatted_content = []
    for paragraph in content_list:
        if capitalize:
            paragraph = paragraph.upper()
        # do not split if a number or capital letter precedes the period
        raw_chunks = re.split(r'((?<!\d|[A-Z])[\.:])', paragraph)
        chunks = merge_chunks(raw_chunks)
        for chunk in chunks:
            total_length += len(chunk)
            t_container = TextContainer(chunk)
            if len(chunk) > 140 and random.random() > 0.75:
                t_container.paragraph = True
            if random.random() < 0.6:
                t_container.italic = True
            formatted_content.append(t_container)

        if len_limit is not None and total_length >= len_limit:
            return formatted_content

    return formatted_content


def filter_paragraphs(content_list, req_chars):
    '''
    find paragraph(s) containing all or (at least) one required character
    '''
    paragraphs_containing_all = [
        p for p in content_list if set(p) >= set(req_chars)
    ]
    if paragraphs_containing_all:
        # paragraph(s) containing all characters have been found
        req_paragraph = random.choice(paragraphs_containing_all)
        num_paragraphs = len(paragraphs_containing_all)
        content_list.insert(0, req_paragraph)

        print(f'matching paragraph ({req_chars} -- {num_paragraphs} found):')
        print('\n'.join(textwrap.wrap(req_paragraph, 70)))
        print()

    else:
        for c_index, char in enumerate(req_chars):
            # paragraphs for individual characters have been found
            paragraphs_containing_one = [
                p for p in content_list if char in p]
            if paragraphs_containing_one:
                req_paragraph = random.choice(
                    paragraphs_containing_one)
                content_list.insert(c_index, f'[{char}] {req_paragraph}')
                print(f'matching paragraph ({char}):')
                print('\n'.join(textwrap.wrap(req_paragraph, 70)))
                print()

            else:
                # nothing has been found for that character
                print(f'no paragraph found for ({char})')

    return content_list


def get_content_from_charset(charset_name):
    '''
    Chain external text files based on a given (validated) charset name,
    split lines into a list, shuffle, and return
    '''

    charset_has_level = re.match(r'..(\d)', charset_name)

    if charset_has_level:
        charset_prefix = charset_name[:2]
        max_charset_level = int(charset_has_level.group(1))
        raw_content = chain_charset_texts(charset_prefix, max_charset_level)

    else:
        # abc or ascii charset, does not have a level
        content_dir = Path(__file__).parent / '_content/'
        text_file_name = f'{charset_name.upper()}.txt'
        text_file_path = content_dir / text_file_name
        raw_content = read_text_file(text_file_path)

    content_list = raw_content.split('\n')
    random.shuffle(content_list)
    return content_list


def get_content_from_text_file(text_file):
    '''
    Read text file and return as a list
    '''

    raw_content = read_text_file(text_file)
    content_list = raw_content.split('\n')
    return content_list


def validate_charset(charset_name):
    try:
        target_charset = eval(f'cs.{charset_name.lower()}')
    except NameError:
        sys.exit(f'Character set "{charset_name}" is not defined')
    return target_charset


def get_glyphs_per_page(font, pt_size):

    ttfont = TTFont(font)
    avg_glyph_width = ttfont['OS/2'].xAvgCharWidth
    upm = ttfont['head'].unitsPerEm

    # A Letter page is 8.5 by 11 inches. 1 inch contains 72 dtp points.
    # Therefore, 11 * 72, divided by the chosen point size * 1.2 (which is the
    # typical leading factor) results in the number of lines possible per page.
    lines_per_page = (11 * 72) / (pt_size * 1.2)
    glyphs_per_line = (8.5 * 72) / (avg_glyph_width / upm * pt_size)
    glyphs_per_page = int(round(lines_per_page * glyphs_per_line))

    return glyphs_per_page


def make_output_name(fonts_a, fonts_b, cs_name, pt, full):
    '''
    Make an output filename based on the input fonts.
    Not completely exhaustive. There could be a lot of combinations, so
    this is erring on simplicity rather than overkill.
    '''
    path_a = Path(fonts_a[0])
    # include the primary font- or folder name
    output_name = f'text proof {path_a.stem}'
    if fonts_b:
        # include the secondary font- or folder name, if it exists.
        # further fonts or folders are ignored.
        path_b = Path(fonts_b[0])
        if path_b.is_file():
            output_name += ' vs'
        output_name += f' {path_b.stem}'

    output_name += f' {cs_name} {pt}pt'

    if full:
        output_name += ' full'

    return output_name


def make_formatted_content(
    content_list, charset,
    len_limit=None, char_filter=None, capitalize=False, full=False
):
    if full:
        # Some characters are hard to find, so the source text might not
        # contain all of the characters for the given charset.
        acceptable_omissions = len(
            set(charset) - set(''.join(content_list)))

        full_content = []
        remaining_charset = charset

        while len(remaining_charset) > acceptable_omissions:
            paragraph, remaining_charset = consume_charset(
                content_list, remaining_charset)
            full_content.append(paragraph)

        formatted_content = format_content(full_content, capitalize)

    else:
        if char_filter:
            content_list = filter_paragraphs(content_list, char_filter)

        formatted_content = format_content(content_list, len_limit, capitalize)

    return formatted_content


def get_fonts(input_paths):
    fonts = []
    for i, path_name in enumerate(input_paths):
        fonts.extend(get_font_paths(Path(path_name)))
    fonts = fontSorter.sort_fonts(fonts, alternate_italics=True)
    return fonts


def main():
    args = get_options()

    fonts_a = get_fonts(args.fonts)
    fonts_b = get_fonts(args.secondary_fonts)

    gpp_count = 0
    for i, font in enumerate(fonts_a + fonts_b):
        # Make temporary fonts, and calculate how many glyphs of the given
        # font may fit on a page
        gpp_count += get_glyphs_per_page(font, args.pt_size)

    # This is not completely representative of the # of glyphs/page,
    # but it is a useful approximation.
    len_limit = gpp_count / (len(fonts_a) + len(fonts_b))

    if args.text_file:
        content_list = get_content_from_text_file(args.text_file)
        output_name = make_output_name(
            args.fonts, args.secondary_fonts,
            'text file', args.pt_size, args.full)
        formatted_content = format_content(content_list, len_limit, False)

    elif args.charset:
        charset_name = args.charset
        charset = validate_charset(charset_name)
        content_list = get_content_from_charset(charset_name)
        output_name = make_output_name(
            args.fonts, args.secondary_fonts,
            charset_name, args.pt_size, args.full)
        formatted_content = make_formatted_content(
            content_list, charset,
            len_limit, args.filter, args.capitalize, args.full)

    else:
        pass

    make_proof(formatted_content, fonts_a, fonts_b, args, output_name)

    if args.charset and args.verbose:
        content_pick = [fc.text for fc in formatted_content]
        analyze_missing(content_pick, content_list, args.charset)


if __name__ == '__main__':
    main()
