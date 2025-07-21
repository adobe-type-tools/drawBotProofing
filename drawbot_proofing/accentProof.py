# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Proof of all accents with a representation of all glyphs using that accent,
and example words for each accent (both upper- and lowercase).
Additionally, words with “merged” non-abc glyphs (such as æðøß) will be shown.

This script is currently limited to AL-3, an extension to AL-4 and beyond is
thinkable.

Input: single font or folder containing font files.

'''

import argparse
import drawBot as db
import subprocess
import random
import re

from pathlib import Path
from .proofing_helpers import fontSorter
from .proofing_helpers.stamps import timestamp
from .proofing_helpers.files import (
    get_font_paths, chain_charset_texts)
from .proofing_helpers.globals import *

DOC_SIZE = 'Letter'
PT_SIZE = 20
MARGIN = PT_SIZE

AL3_CMB_ACCENTS = {
    # combining accents and letters they’re used in
    0x0300: 'ÀÈÌÒÙàèìòù',
    0x0301: 'ÁÉÍÓÚÝáéíóúýĆćĹĺŃńŔŕŚśŹź',
    0x0302: 'ÂÊÎÔÛâêîôû',
    0x0303: 'ÃÑÕãñõ',
    0x0304: 'ĀāĒēĪīŌōŪū',
    0x0306: 'ĂăĞğ',
    0x0307: 'ĖėĠġİŻżṄṅ',
    0x0308: 'ÄËÏÖÜäëïöüÿŸ',
    0x030A: 'ÅåŮů',
    0x030B: 'ŐőŰű',
    0x030C: 'ČčĎďĚěĽľŇňŘřŠšŤťŽž',
    0x0326: 'ȘșȚț',
    0x0327: 'ÇçĶķŖŗŞşŢţ',
    0x0328: 'ĄąĘęĮįŲų',
}
AL4_CMB_ACCENTS = {
    # not used for this script
    0x0323: 'ḌḍḤḥḶḷṂṃṆṇṚṛṢṣṬṭẒẓẠạẸẹỊịỌọỢợỤụỰựỴỵ',
    0x0309: 'ẢảẨẩẲẳẺẻỂểỈỉỎỏỔổỞởỦủỬửỶỷ',
    0x031B: 'ƠơƯư',
    0x0331: 'ḎḏḺḻṈṉṞṟṮṯ',
    0x032E: 'Ḫḫ',
}
AL3_MERGED = {
    # merged non-abc characters in AL3
    0x0131: 'ı',
    0x00DF: 'ß',
    0x00E6: 'æ',
    0x00F0: 'ð',
    0x00F8: 'ø',
    0x00FE: 'þ',
    0x0111: 'đ',
    0x0142: 'ł',
    0x0153: 'œ',
}
LC_ONLY = [
    0x017F,  # longs
    0x00DF,  # germandbls
    0x0131,  # dotlessi
]


def filter_content(filter_chars, content):
    '''
    remove filter_chars from content
    '''
    return re.sub(f'[{re.escape(filter_chars)}]', '', content)


def collect_al3_words():
    raw_content = chain_charset_texts('AL', 3)
    filtered_content = filter_content(
        '*,.;:(){{}}[]¹²³⁴⁵"¿¡!?/\'“”„-–—<>+=', raw_content)
    al3_words = filtered_content.split()
    return al3_words


def make_longs_wordlist(wordlist):
    '''
    It is rare for an ſ to occur in the wild, so every word with s is
    converted to be a word with ſ.

    ſ can never occur at the end of a word.
    '''
    longs_words = []
    for word in wordlist:
        if len(word) >= 3 and 's' in word[:-1]:
            longs_word = word[:-1].replace('s', 'ſ') + word[-1]
            longs_words.append(longs_word)
    return longs_words


def make_pages(content, my_font):
    db.newPage(DOC_SIZE)

    fs = db.FormattedString(
        content,
        font=my_font,
        fontSize=PT_SIZE,
        fallbackFont=ADOBE_BLANK,
        openTypeFeatures=dict(liga=True),
    )

    fs_time = db.FormattedString(
        timestamp(readable=True),
        font=FONT_MONO,
        fontSize=6,
    )
    overflow = db.textBox(
        fs, (
            4 * MARGIN, 3 * MARGIN,
            db.width() - 6 * MARGIN, db.height() - 5 * MARGIN)
    )
    db.textBox(
        fs_time,
        (4 * MARGIN, 0, db.width(), 1.75 * MARGIN)
    )
    if overflow and len(str(overflow).strip()):
        make_pages(overflow, my_font)


def make_output_name(input_path, font_list):
    name = ['accentProof']

    if len(font_list) == 1:
        name.append(font_list[0].stem)
    else:
        name.append(input_path.name)

    return ' '.join(name)


def make_example_chars(codepoint):
    if codepoint in AL3_CMB_ACCENTS.keys():
        example_chars = ' '.join(sorted(AL3_CMB_ACCENTS.get(codepoint)))
    elif codepoint in LC_ONLY:
        example_chars = chr(codepoint)
    else:
        example_chars = chr(codepoint).upper() + ' ' + chr(codepoint)
    return example_chars


def make_example_words(codepoint, words_lc, num_words=10, randomize=True):
    if randomize:
        random.shuffle(words_lc)
    words_lc = words_lc[:num_words]
    words_uc = [word.upper() for word in words_lc]

    if codepoint in LC_ONLY:
        example_words = words_lc
    elif codepoint == 0x030C:  # combining caron
        # make sure that both forms of the caron are shown
        example_words = words_uc + ['neďeľné šťastný'] + words_lc[:num_words-2]
    else:
        example_words = words_uc + words_lc

    return " ".join(example_words)


def make_content_list(input_word_dict):
    content_list = []
    for codepoint, word_list in sorted(input_word_dict.items()):
        content_list.append(
            f'{make_example_chars(codepoint)} – '
            f'{make_example_words(codepoint, word_list)}\n')
    return content_list


def find_words_containing(input_dict, word_list):
    '''
    From a list of words, find all words containing a character.
    If the character is a combining mark, find all words with accented
    glyphs that could be composed using that combining mark.
    '''
    output = {}
    for codepoint, input_chars in input_dict.items():
        if len(input_chars) == 1:
            # single (merged) character
            regex = re.compile(rf'(\S*?({input_chars})\S*?)')
        else:
            # list of accented glyphs
            regex = re.compile(rf'(\S*?({"|".join(input_chars)})\S*?)')
        words_filtered = filter(regex.match, word_list)
        words_lower = sorted(set([word.lower() for word in words_filtered]))
        output[codepoint] = words_lower
    return output


def get_options(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        'input',
        metavar='INPUT',
        help='font file or folder containing font files',
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
    input_path = Path(args.input)
    font_list = fontSorter.sort_fonts(
        get_font_paths(input_path), alternate_italics=True)

    if font_list:
        al3_words = collect_al3_words()
        accent_words = find_words_containing(AL3_CMB_ACCENTS, al3_words)
        precomp_words = find_words_containing(AL3_MERGED, al3_words)

        content = '\n'.join(
            make_content_list(accent_words) +
            make_content_list(precomp_words))

        db.newDrawing()
        for font_path in font_list:
            make_pages(content, font_path)

        output_name = make_output_name(input_path, font_list)
        output_path = Path(f'~/Desktop/{output_name}.pdf').expanduser()

        db.saveImage(output_path)
        db.endDrawing()
        if not args.headless:
            subprocess.call(['open', output_path])

    else:
        print('No fonts (OTF or TTF) found.')


if __name__ == '__main__':
    main()
