# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Proof of all Latin accents supported by a given font, with example words for
each accent (both upper- and lowercase). Additionally, words with “atomic”
Latin base glyphs (such as æðøß) will be shown.

Input:
* font file(s), or folder(s) containing font files

'''

import argparse
import drawBot as db
import subprocess
import random
import re
import unicodedata

from fontTools.ttLib import TTFont
from pathlib import Path

from .proofing_helpers import fontSorter
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.files import get_font_paths, chain_charset_texts
from .proofing_helpers.names import get_ps_name
from .proofing_helpers.stamps import timestamp
from .proofing_helpers.globals import FONT_MONO, ADOBE_BLANK


def get_supported_chars(font):
    '''
    characters supported by a font
    '''
    cmap = TTFont(font)['cmap'].getBestCmap()
    mapped_chars = set([chr(c) for c in cmap.keys()])
    return mapped_chars


def filter_content(filter_chars, content):
    '''
    remove filter_chars from content
    '''
    return re.sub(f'[{re.escape(filter_chars)}]', '', content)


def collect_words():
    raw_content = chain_charset_texts('AL', 5)
    filtered_content = filter_content(
        '*,.;:(){{}}[]¹²³⁴⁵"¿¡!?/\'“”„-–—<>+=', raw_content)
    words = filtered_content.split()
    return words


def make_pages(content, my_font):
    db.newPage('Letter')
    ps_name = get_ps_name(my_font)

    pt_size = 20
    margin = pt_size
    text_area = (
        4 * margin, 3 * margin,
        db.width() - 6 * margin, db.height() - 5 * margin)

    content = db.FormattedString(
        content,
        font=my_font,
        fontSize=pt_size,
        fallbackFont=ADOBE_BLANK,
        openTypeFeatures=dict(liga=True),)

    caption = db.FormattedString(
        f'{ps_name} | {timestamp(readable=True)}',
        font=FONT_MONO,
        fontSize=6,)

    overflow = db.textBox(content, text_area)

    db.textBox(
        caption,
        (4 * margin, 0, db.width(), 1.75 * margin)
    )
    if overflow and len(str(overflow).strip()):
        # avoid starting a page with a line break
        overflow = str(overflow).lstrip('\n')
        make_pages(overflow, my_font)


def make_output_name(font_list):
    name = ['accent proof']
    chunks = []
    folders = sorted(set([font.stem for font in font_list]))

    if len(folders) >= 1:
        chunks.append(folders[0])
    if len(folders) >= 2:
        chunks.append(folders[1])
    if len(folders) >= 3:
        chunks.append('etc')

    name.append(', '.join(chunks))
    return ' '.join(name)


def get_example_chars(cp, accent_dict, supported_chars):

    if cp in accent_dict.keys():
        example_chars = accent_dict.get(cp)
        supported = set(example_chars) & set(supported_chars)
        return ' '.join(sorted(supported))

    else:
        if chr(cp).upper() == chr(cp):
            # does not have an uppercase variant
            example_chars = [chr(cp)]
        elif chr(cp) == 'ſ':
            example_chars = [chr(cp)]
        else:
            example_chars = [chr(cp).upper(), chr(cp)]
        supported = set(example_chars) & set(supported_chars)

        if supported:
            return ' '.join(sorted(supported))


def get_example_words(cp, words, supported_chars, length=10, randomize=True):

    if randomize:
        random.shuffle(words)
    words = words[:length]
    words_uc = [word.upper() for word in words]

    if unicodedata.category(chr(cp)) == 'Mn':  # combining marks
        if cp == 0x030C:  # combining caron
            # make sure that both forms of the caron are shown
            example_words = (
                words_uc + ['neďeľné šťastný'] + words)
        else:
            example_words = words_uc + words

    else:  # atomic latin
        if chr(cp).upper() == chr(cp):
            # no uppercase available
            example_words = words
        elif len(chr(cp).upper()) > 1:
            # uppercase splits into 2 (ß → SS)
            example_words = words
        elif cp == ord('ſ'):
            # long s:
            example_words = [
                # ſ can never occur at the end of a word.
                word.replace('s', 'ſ') for word in words if not
                word.endswith('s')]
        else:
            example_words = words_uc + words

    supported_words = [
        word for word in example_words if set(word) < set(supported_chars)]
    return " ".join(supported_words)


def make_content_list(font, words_for_cp, accents_dict):
    content_list = []
    supported_chars = get_supported_chars(font)

    for cp, words in sorted(words_for_cp.items()):
        example_chars = get_example_chars(cp, accents_dict, supported_chars)
        example_words = get_example_words(cp, words, supported_chars)
        if example_chars and example_words:
            content_list.append(f'{example_chars} – {example_words}\n')
    return content_list


def find_words_containing(input_dict, words):
    '''
    From a list of words, find all words containing a character.
    If the character is a combining mark, find all words with accented
    glyphs that could be composed using that combining mark.
    '''
    output = {}
    for cp, input_chars in input_dict.items():
        if len(input_chars) == 1:
            # single (merged) character
            input_char = input_chars[0]
            if input_char == 'ſ':
                input_char = 's'
            regex = re.compile(rf'(\S*?({input_char})\S*?)')
        else:
            # list of accented glyphs
            regex = re.compile(rf'(\S*?({"|".join(input_chars)})\S*?)')
        words_filtered = filter(regex.match, words)
        words_lower = sorted(set([word.lower() for word in words_filtered]))
        if len(words_lower) > 1:
            output[cp] = words_lower
    return output


def get_cmb_accents_dict(report=False):
    '''
    Create a dictionary of combining accents and their use, i.e.

    # COMBINING GRAVE ACCENT
    0x0300: 'ÀÈÌÒÙàèìòùǸǹẀẁỲỳ',

    # COMBINING ACUTE ACCENT
    0x0301: 'ÁÉÍÓÚÝáéíóúýĆćĹĺŃńŔŕŚśŹźǴǵǼǽǾǿḰḱḾḿṔṕẂẃ',

    # COMBINING CIRCUMFLEX ACCENT
    0x0302: 'ÂÊÎÔÛâêîôûĈĉĜĝĤĥĴĵŜŝŴŵŶŷẐẑ',

    Limited to those Latin base glyphs which cannot themselves be decomposed.
    '''

    accents_to_examples = {}

    # characters in the BMP which have decomposition
    decomposing = [
        cp for cp in range(0xFFFF + 1) if unicodedata.decomposition(chr(cp))]

    for cp in decomposing:
        decomposition = unicodedata.decomposition(chr(cp))
        # make sure the decomposition consists of 2 code points
        if re.match(r'[0-9A-F]{4} [0-9A-F]{4}', decomposition):
            hex_base, hex_accent = decomposition.split()
            cp_base = int(hex_base, 16)
            cp_accent = int(hex_accent, 16)
            # we are focusing on Latin base glyphs, and single-level accents.
            if (
                'LATIN' in unicodedata.name(chr(cp_base)) and
                cp_base not in decomposing
            ):
                accents_to_examples.setdefault(cp_accent, []).append(chr(cp))

    if report:
        for cp_accent, char_list in accents_to_examples.items():
            print(f'# {unicodedata.name(chr(cp_accent))}')
            print(f'0x{cp_accent:04X}: \'{"".join(char_list)}\',')
            print()

    return accents_to_examples


def get_atomic_latin(start=0):

    atomic_latin_basic = [
        cp for cp in range(start, 0xFFFF + 1) if not
        unicodedata.decomposition(chr(cp)) and
        'LATIN' in unicodedata.name(chr(cp), '')]

    atomic_latin_outliers = [
        # characters with compatibility decomposition, such as ſ
        cp for cp in range(start, 0xFFFF + 1) if
        '<compat>' in unicodedata.decomposition(chr(cp)) and
        'LATIN' in unicodedata.name(chr(cp), '') and
        'LETTER' in unicodedata.name(chr(cp), '') and
        unicodedata.category(chr(cp)) in ['Ll', 'Lu']
    ]

    atomic_latin = sorted(atomic_latin_basic + atomic_latin_outliers)

    atomic_latin_lc = list(filter(
        lambda cp: unicodedata.category(chr(cp)) == 'Ll', atomic_latin))

    atomic_latin_uc = list(filter(
        lambda cp: unicodedata.category(chr(cp)) == 'Lu', atomic_latin))

    atomic_latin_other = list(filter(
        lambda cp: unicodedata.category(chr(cp)) == 'Lo', atomic_latin))

    atomic = list(atomic_latin_lc)

    for cp in atomic_latin_uc:
        uc_char = chr(cp)
        cp_lower = ord(uc_char.lower())
        if cp_lower not in atomic_latin_lc:
            # only-uppercase letters, of which there don’t seem to be any
            atomic.append(cp)

    atomic += atomic_latin_other
    return sorted(atomic)


def get_options(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )
    parser.add_argument(
        'input',
        metavar='INPUT',
        nargs='+',
        help='font file(s) or folder(s)',
    )
    parser.add_argument(
        '--headless',
        default=False,
        action='store_true',
        help='do not open result PDF after generating',
    )
    return parser.parse_args(args)


def main(test_args=None):
    args = get_options(test_args)
    accents_dict = get_cmb_accents_dict()
    atomic = get_atomic_latin(start=ord('ß'))
    atomic_dict = {cp: chr(cp) for cp in atomic}

    font_list = []
    for item in args.input:
        # could be individual fonts or folder of fonts.
        ip = Path(item)
        # sort them one-by-one
        font_list.extend(
            fontSorter.sort_fonts(get_font_paths(ip), alternate_italics=True))

    if font_list:
        words = collect_words()
        accent_words = find_words_containing(accents_dict, words)
        atomic_words = find_words_containing(atomic_dict, words)
        db.newDrawing()

        for font_path in font_list:
            content = '\n'.join(
                make_content_list(font_path, accent_words, accents_dict) +
                make_content_list(font_path, atomic_words, accents_dict))
            make_pages(content, font_path)

        output_name = make_output_name(font_list)
        output_path = Path(f'~/Desktop/{output_name}.pdf').expanduser()

        db.saveImage(output_path)
        db.endDrawing()
        if not args.headless:
            subprocess.call(['open', output_path])

    else:
        print('No fonts (OTF or TTF) found.')


if __name__ == '__main__':
    main()
