# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates example paragraphs corresponding to a given character set.
Either prints a single page with random subset of the charset, or consumes
the full charset systematically, to create a multipage document.

Known bug:
line spacing may become inconsistent (this is a macOS limitation caused by
the vertical metrics in a given fallback font.)

Input: folder containing fonts, or single font file.

'''

import os
import re
import sys

import argparse
import random
import subprocess
import textwrap

import drawBot as db

from proofing_helpers import fontSorter
from proofing_helpers.charsets import *
from proofing_helpers.helpers import list_uni_names
from proofing_helpers.files import (
    get_font_paths, chain_charset_texts, read_text_file, make_temp_font)
from proofing_helpers.stamps import timestamp


class TextContainer(object):
    def __init__(self, text, italic=False, paragraph=False):
        self.text = text.strip()
        self.italic = italic
        self.paragraph = paragraph


def get_options():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'input',
        nargs='+',
        help='font file or folder')

    parser.add_argument(
        '-s', '--sec',
        metavar='FONT',
        help='secondary font file or folder')

    parser.add_argument(
        '-f', '--filter',
        action='store',
        metavar='ABC',
        help='required characters')

    parser.add_argument(
        '-c', '--charset',
        action='store',
        default='AL3',
        help='character set')

    parser.add_argument(
        '--capitalize',
        action='store_true',
        default=False,
        help='capitalize output')

    parser.add_argument(
        '-p', '--pointsize',
        action='store',
        default=10,
        type=int,
        help='point size for sample')

    parser.add_argument(
        '-a', '--full',
        action='store_true',
        help='consume whole character set')

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
    tries to consume a character set with example words
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
    print('{} ({}):\n{}\n'.format(
        message,
        len(characters),
        '\n'.join(
            textwrap.wrap(' '.join(sorted(characters)), wrap_length))
    )
    )


def analyze_missing(content_pick, raw_content, charset_name=al3):
    '''
    Print out some stats about the chosen character set,
    which characters were used in the sample, etc.
    '''
    abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    charset = eval(charset_name)
    missing_abc = set(abc) - set(''.join(content_pick))
    missing_charset = set(charset) - set(''.join(content_pick))
    missing_cset_source = set(charset) - set(raw_content)

    message_with_charset(charset_name.upper(), charset)

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
        list_uni_names(missing_cset_source)


def make_proof(content, output_name, orig_fonts, fonts, fonts_sec=[], multipage=False):
    db.newDrawing()
    for f_index, font in enumerate(fonts):
        make_page(content, orig_fonts, fonts, fonts_sec, f_index, multipage)

    pdf_path = f'~/Desktop/{output_name}.pdf'
    db.saveImage(pdf_path)
    db.uninstallFont(ADOBE_BLANK)

    db.endDrawing()
    print('saved to {}'.format(pdf_path))
    subprocess.call(['open', os.path.expanduser(pdf_path)])


def make_page(content, orig_fonts, fonts, fonts_sec, f_index=0, multipage=False):

    db.newPage(DOC_SIZE)
    if charset_name == 'abc':
        # We do not want any non-ABC characters (such as the hyphen)
        # in an ABC-only proof
        db.hyphenation(False)
    else:
        db.hyphenation(True)

    fs = db.FormattedString(
        fontSize=PT_SIZE,
        # fallbackFont=ADOBE_BLANK,
        openTypeFeatures=dict(
            liga=True,
            # onum=True,
            # pnum=True,
            # tnum=True,
        ),
    )

    font_file_string = os.path.basename(orig_fonts[f_index])  # use original filename, not temp
    # make sure primary and secondary font lists have even length
    if fonts_sec:
        while len(fonts_sec) < len(fonts):
            fonts_sec.append(fonts_sec[-1])

        while len(fonts) < len(fonts_sec):
            fonts.append(fonts[-1])
        font_file_string += ' + {}'.format(
            os.path.basename(fonts_sec[f_index]))

    for text_item in content:
        if text_item.italic and fonts_sec:
            fs.append('%s' % text_item.text, font=fonts_sec[f_index])
        else:
            fs.append('%s' % text_item.text, font=fonts[f_index])

        if text_item.paragraph:
            fs.append('\n\n')
        else:
            fs.append(' ')

    fs_footer = db.FormattedString(
        '{} | {} | {} pt'.format(
            timestamp(readable=True),
            font_file_string,
            PT_SIZE
        ),
        font=FONT_MONO,
        fontSize=6,
    )

    overflow = db.textBox(
        fs, (
            6 * MARGIN,
            5 * MARGIN,
            db.width() - 9 * MARGIN,
            db.height() - 7 * MARGIN
        )
    )
    db.textBox(
        fs_footer,
        (6 * MARGIN, 0, db.width(), 3 * MARGIN)
    )

    if overflow and multipage:
        overflowing_item = [
            (index, item) for (index, item) in list(enumerate(content)) if (
                # 10 is a totally random number
                str(overflow[:10]) in item.text)]
        if overflowing_item:
            new_start_index = overflowing_item[0][0]
        else:
            new_start_index = 5
        remaining_content = content[new_start_index:]
        make_page(remaining_content, fonts, fonts_sec, f_index, multipage=True)


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
            content_pick.append(chunk)
            formatted_content.append(t_container)

        if len_limit is not None and total_length >= len_limit:
            return formatted_content

    return formatted_content


if __name__ == '__main__':

    args = get_options()

    DOC_SIZE = 'Letter'
    PT_SIZE = args.pointsize
    MARGIN = 12

    assets_path = os.path.dirname(__file__)
    ADOBE_BLANK = db.installFont(
        os.path.join(assets_path, '_fonts/AdobeBlank.otf'))
    FONT_MONO = os.path.join(assets_path, '_fonts/SourceCodePro-Regular.otf')

    # A Letter page is 8.5 by 11 inches. 1 inch contains 72 dtp points.
    # Therefore, 11 * 72, divided by the chosen point size * 1.2 (which is the
    # typical leading factor) results in the number of lines possible per page.
    lines_per_page = (11 * 72) / (PT_SIZE * 1.2)

    # Similar calculation, and simplified assumption for an average glyph to be
    # 250 units wide.
    glyphs_per_line = (8.5 * 72) / (250 / 1000 * PT_SIZE)

    glyphs_per_page = int(round(lines_per_page * glyphs_per_line))

    req_chars = args.filter
    charset_name = args.charset.lower()
    charset_digit = re.match(r'..(\d)', charset_name)

    if charset_digit:
        max_charset_level = int(charset_digit.group(1))
        charset_prefix = charset_name[:2]
        raw_content = chain_charset_texts(charset_prefix, max_charset_level)

    else:
        text_file_name = f'_content/{charset_name.upper()}.txt'
        raw_content = read_text_file(text_file_name)

    try:
        target_charset = eval(charset_name)
    except NameError:
        sys.exit(f'Character set "{charset_name}" is not defined')

    content_list = raw_content.split('\n')
    random.shuffle(content_list)
    content_pick = []
    output_name = 'text proof'

    input_fonts = []
    for item in args.input:
        if os.path.isdir(item):
            input_fonts.extend(get_font_paths(item))
        else:
            input_fonts.append(item)
            base_name = os.path.splitext(os.path.basename(args.input[0]))[0]
            output_name += f' {base_name}'

    sorted_fonts = fontSorter.sort_fonts(
        input_fonts, alternate_italics=True)
    fonts = [make_temp_font(i, font) for i, font in enumerate(sorted_fonts)]

    if fonts:
        fonts_sec = []
        if args.sec:
            if os.path.isdir(args.sec):
                output_name += f' {os.path.split(args.sec)[-1]}'
                fonts_sec = get_font_paths(args.sec)
            elif os.path.isfile(args.sec) and os.path.exists(args.sec):
                base_name = os.path.splitext(os.path.basename(args.sec))[0]
                output_name += f' vs {base_name}'
                fonts_sec = [args.sec]
            else:
                sys.exit('invalid alternate input.')
        output_name += f' {charset_name} {args.pointsize}pt'
        if args.full:
            output_name += ' full'
            full_content = []
            paragraph, remaining_charset = consume_charset(
                content_list, target_charset)

            if charset_name == 'al2':
                possible_remainder = 32
            else:
                possible_remainder = 13

            full_content.append(paragraph)
            while len(remaining_charset) > possible_remainder:
                # could not find example words for
                # 13 characters in AL3,
                # 32 characters in AL2, etc.

                paragraph, remaining_charset = consume_charset(
                    content_list, remaining_charset)
                full_content.append(paragraph)

            formatted_content = format_content(
                full_content, capitalize=args.capitalize)

            final_container = TextContainer(
                ' '.join(target_charset), paragraph=True)
            formatted_content.append(TextContainer('\n', paragraph=True))
            formatted_content.append(final_container)
            make_proof(
                formatted_content, output_name,
                sorted_fonts, fonts, fonts_sec,
                multipage=True)

        else:
            if req_chars:
                all_chars_paragraphs = [
                    p for p in content_list if set(p) >= set(req_chars)
                ]
                if all_chars_paragraphs:
                    req_paragraph = random.choice(all_chars_paragraphs)
                    content_list.insert(0, req_paragraph)
                    print(u'required paragraph ({} -- {} found):'.format(
                        req_chars, len(all_chars_paragraphs)))
                    print('\n'.join(textwrap.wrap(req_paragraph, 70)))
                    print()

                else:
                    for c_index, char in enumerate(req_chars):
                        found_paragraphs = [
                            p for p in content_list if char in p]
                        if found_paragraphs:
                            req_paragraph = random.choice(found_paragraphs)
                            print(u'required paragraph ({}):'.format(char))
                            print('\n'.join(textwrap.wrap(req_paragraph, 70)))
                            print()
                            content_list.insert(
                                c_index,
                                '[{}] {}'.format(char, req_paragraph))
                        else:
                            print(
                                'no paragraph available for ({})'.format(char))

            formatted_content = format_content(
                content_list,
                len_limit=glyphs_per_page,
                capitalize=args.capitalize)

            make_proof(formatted_content, output_name, sorted_fonts, fonts, fonts_sec)

        analyze_missing(content_pick, raw_content, charset_name)

    else:
        print('No fonts found.')
