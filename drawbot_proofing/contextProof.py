# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates example pages for usage of a specific letter or letter combination.

Needs a word list as an input file, such as the word lists available at
https://github.com/hermitdave/FrequencyWords/tree/master/content/2016

Input: font file(s) or folder of fonts.

'''

import sys

import argparse
import subprocess

import drawBot as db
from pathlib import Path

from .proofing_helpers.files import get_font_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import *
from .proofing_helpers.fontSorter import sort_fonts
from .proofing_helpers.stamps import timestamp

default_wl = Path(__file__).parent / "_content" / "en_10k.txt"


def get_options():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )

    parser.add_argument(
        '-p', '--point_size',
        default=20,
        action='store',
        type=int,
        help='font size')

    parser.add_argument(
        '-w', '--wordlist',
        default=default_wl,
        action='store',
        help='wordlist file')

    parser.add_argument(
        '-d', '--date',
        default=False,
        action='store_true',
        help='date output file')

    parser.add_argument(
        '-a', '--word_amount',
        default=300,
        action='store',
        type=int,
        help='max example words/page')

    parser.add_argument(
        '-k', '--kerning_off',
        default=False,
        action='store_true',
        help='switch off kerning')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '-l', '--letters',
        action='store',
        help='letter(s) to proof')

    group.add_argument(
        '-c', '--combination',
        action='store',
        help='combination to proof')

    parser.add_argument(
        'input',
        nargs='+',
        help='input font file(s)')

    return parser.parse_args()


def extract_x_words(wordlist_path, depth=1000):
    '''
    Extract `depth` first lines from a word list.
    This is based on the `FrequencyWords` lists, which follow this syntax:
    (word | word count)

    die 5453
    ek 4892
    nie 4499

    Only the word, not the count is included in the output list.

    '''

    with open(wordlist_path, 'r') as f:
        data = f.read().splitlines()
    data = [word for word in data if len(word) >= 4]
    if len(data) > depth:
        data = data[:depth]
    data = [word.split(' ')[0] for word in data]
    return data


def filter_wordlist(wordlist_path, letters='', combination=False):
    '''
    Filter wordlist by desired letter or combination.

    '''
    all_words = extract_x_words(wordlist_path, depth=30000)
    if letters:
        if combination is True:
            if letters.istitle():
                all_words.extend([word.title() for word in all_words])
            if letters.isupper():
                all_words.extend([word.upper() for word in all_words])
            return [word for word in all_words if letters in word]
        else:
            return [word for word in all_words if set(letters) & set(word)]
    else:
        return all_words


def make_proof(args, content, font_paths, output_path):

    db.newDrawing()
    MARGIN = 30

    if args.kerning_off:
        kerning_flag = ' (no kerning) '
        fea_dict = {'kern': False}
    else:
        kerning_flag = ' '
        fea_dict = {}

    for font in font_paths:
        db.newPage('LetterLandscape')

        stamp = db.FormattedString(
            f'{font.name}{kerning_flag}| {timestamp(readable=True)}',
            font=FONT_MONO,
            fontSize=8,
            align='right')

        db.text(stamp, (db.width() - MARGIN, MARGIN * 2 / 3))
        fs = db.FormattedString(
            content,
            font=font,
            fontSize=args.point_size,
            fallbackFont=ADOBE_BLANK,
            openTypeFeatures=fea_dict,
        )
        db.textBox(fs, (
            MARGIN, MARGIN,
            db.width() - 2 * MARGIN,
            db.height() - 2 * MARGIN
        ))

    db.saveImage(output_path)
    db.endDrawing()

    subprocess.call(['open', output_path])


def make_output_path(args):
    if args.letters:
        if len(args.letters) > 1:
            flag = 'letters'
        else:
            flag = 'letter'
        output_name = f'contextProof ({flag} {args.letters})'
    else:
        output_name = f'contextProof (combination {args.combination})'

    if args.date:
        output_name = f'{timestamp()} ' + output_name

    return Path(f'~/Desktop/{output_name}.pdf').expanduser()


def main():
    args = get_options()
    wordlist_path = Path(args.wordlist)
    output_path = make_output_path(args)

    font_list = []
    for input_path in args.input:
        font_list.extend(get_font_paths(input_path))
    input_paths = sort_fonts(font_list)

    limit = args.word_amount
    if args.letters:
        req_chars = args.letters
        combo_mode = False
    else:
        req_chars = args.combination
        combo_mode = True

    if wordlist_path.exists():
        content = filter_wordlist(wordlist_path, req_chars, combo_mode)
    else:
        sys.exit('No default word list found.')

    if content:
        make_proof(args, ' '.join(content[:limit]), input_paths, output_path)
    else:
        sys.exit(f'no words for {req_chars} found')


if __name__ == '__main__':
    main()
