# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import re

from itertools import chain
from pathlib import Path
from .names import get_ps_name

opsz_names = [
    ['null'],
    ['caption', 'capt'],
    ['5pt'],
    ['7pt'],
    ['smalltext', 'smtxt'],
    ['text'],
    ['normal'],
    ['subhead', 'subh'],
    ['display', 'disp'],
    ['large'],
    ['poster'],
]
width_names = [
    ['extracondensed', 'extracond', 'xcondensed', 'xcond'],
    ['narrow'],
    ['condensed', 'cond', 'cnd'],
    ['semicondensed', 'semicond', 'semicnd', 'semicn'],
    ['normal'],
    ['semiextended', 'semiext'],
    ['extended'],
    ['expanded'],
    ['wide'],
    ['xwide'],
]
weight_names = [
    'hair',
    'ultralight',
    'thin',
    'extralight',
    'light',
    'semilight',
    'book',
    'regular',
    'medium',
    'semibold',
    'bold',
    'extrabold',
    'heavy',
    'black',
    'ultra',
    'fat',
]

DEFAULT_SCORE = (
    opsz_names.index(['normal']),
    width_names.index(['normal']),
    weight_names.index('regular'))


def find_longest_match(attr_list, match_indices):
    found_names = [
        (len(name), name) for (name_index, name) in enumerate(attr_list) if
        name_index in match_indices
    ]
    _, longest_name = sorted(found_names)[-1]
    longest_name_index = attr_list.index(longest_name)
    return longest_name_index


def make_psname_dict(font_files):
    '''
    Dictionary of PS names to font files that have them.
    The dict values are lists, because multiple fonts might have the
    same PS name.
    '''
    psname_dict = {}
    for font_file in font_files:
        psname = get_ps_name(font_file)
        psname_dict.setdefault(psname, []).append(font_file)
    return psname_dict


def get_attr_score(ps_name, attr_list, fallback):
    '''
    Get score for one specific attribute
    (opsz, width, weight)
    '''
    name_matches = []
    for index, variant in enumerate(attr_list):
        if isinstance(variant, list):
            # lists of equivalent variants (like Cnd and Condensed)
            for sub_variant in variant:
                rx = re.compile(
                    rf'(.+?)?({sub_variant})(.+?)?', re.IGNORECASE)
                if re.match(rx, ps_name):
                    name_matches.append(index)
        else:
            # simple style names, like Regular
            rx = re.compile(
                rf'(.+?)?({variant})(.+?)?', re.IGNORECASE)
            if re.match(rx, ps_name):
                name_matches.append(index)

    if name_matches:
        score = find_longest_match(attr_list, name_matches)
    else:
        score = attr_list.index(fallback)
    return score


def get_italic_score(ps_name):
    # Does the PS name contain Italic?
    it_score = 0
    italic_match = re.match(r'.*(it)(alic)?.*', ps_name, re.IGNORECASE)
    if italic_match:
        it_score = 1
    return it_score


def get_index_score(ps_name):
    # A PS name may contain an index number -- return it if it exists
    index_score = 0
    index_match = re.match(r'.+?(\d+?)$', ps_name)
    if index_match:
        index_score = int(index_match.group(1))
    return index_score


def test_outlier(ps_name):
    '''
    Check if any of the given attributes match the ps name.
    If not, the name cannot be sorted (e.g. Acumin-Whatever).
    '''
    all_attrs = (
        list(chain.from_iterable(opsz_names)) +
        list(chain.from_iterable(width_names)) +
        weight_names + ['Italic', 'Ita', 'It'])
    if not any([
        re.match(rf'(.+?)?({attr})(.+?)?', ps_name, re.IGNORECASE) for
        attr in all_attrs
    ]):
        return True
    return False


def make_hash(opsz_score, width_score, weight_score, index_score, it_score):
    return (
        f'{opsz_score:03d}{width_score:03d}'
        f'{weight_score:03d}{index_score:02d}{it_score}')


def get_score(ps_name, alternate_italics=False):
    '''
    calculcate a score for a given PS name, consisting of
    opsz, width, weight, index, italic.

    If Italics are supposed to be inserted between the styles, the score is
    opsz, width, weight, index (italic attribute is counted as part of weigh)

    For example:

    006004007000 AcuminPro-Regular
    006 = opsz
    004 = wdth
    007 = wght
    00 = index
    0 = italic
    '''

    opsz_score = get_attr_score(ps_name, opsz_names, ['normal'])
    width_score = get_attr_score(ps_name, width_names, ['normal'])
    weight_score = get_attr_score(ps_name, weight_names, 'regular')
    index_score = get_index_score(ps_name)
    it_score = get_italic_score(ps_name)

    if not alternate_italics and it_score == 1:
        # If Italics are not to be alternated, move them after the Romans
        # by way of increasing the weight score
        weight_score += 100

    if (opsz_score, width_score, weight_score) == DEFAULT_SCORE:
        if test_outlier(ps_name):
            opsz_score = 999
            width_score = 999
            weight_score = 999

    style_hash = make_hash(
        opsz_score, width_score, weight_score,
        index_score, it_score)

    return style_hash


def sort_ps_names(ps_name_list, alternate_italics=False, debug=False):
    '''
    Sort a list of PS names according to a hard-coded list of style names.
    '''

    matches = {}
    for ps_name in ps_name_list:
        style_hash = get_score(ps_name, alternate_italics)
        # matches.setdefault(ps_name, []).append(int(style_hash))
        matches.setdefault(int(style_hash), []).append(ps_name)

    # make sure the matches are sorted alphabetically per-style,
    # in case more than one family is sorted
    for score, font_list in matches.items():
        font_list.sort()
    # score_dict = {min(score_list): f for f, score_list in matches.items()}

    sorted_name_lists = [f for _, f in sorted(matches.items())]
    sorted_names = list(chain.from_iterable(sorted_name_lists))

    return sorted_names


def sort_fonts(font_files, alternate_italics=False, debug=False):
    if len(font_files) <= 1:
        return font_files

    psname_dict = make_psname_dict(font_files)
    sorted_names = sort_ps_names(
        psname_dict.keys(), alternate_italics, debug)
    sorted_files = []
    for ps_name in sorted_names:
        sorted_files.extend(psname_dict.get(ps_name))

    return sorted_files


def get_font_paths(directory):
    ufo_paths = list(directory.rglob('*.ufo'))
    otf_paths = list(directory.rglob('*.otf'))
    ttf_paths = list(directory.rglob('*.ttf'))

    if ufo_paths:
        return ufo_paths
    elif otf_paths:
        return otf_paths
    else:
        return ttf_paths


def get_args(args=None):
    import argparse

    parser = argparse.ArgumentParser(
        description='Font Sorting Test')

    parser.add_argument(
        'input_dir',
        action='store',
        metavar='FOLDER',
        help=(
            'Directory which may contain (in order of preference) '
            'UFOs, OTFs, or TTFs.'))

    parser.add_argument(
        '-i', '--alternate_italics',
        action='store_true',
        default=False,
        help=('Italics adjacent to their related Romans'))

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        default=False,
        help=('Debug output'))

    return parser.parse_args(args)


def main(test_args=None):
    '''
    A test to sort the fonts
    '''
    args = get_args(test_args)
    input_dir = Path(args.input_dir)
    print(input_dir)
    if input_dir.exists():
        fonts_unsorted = get_font_paths(input_dir)
        fonts_sorted = sort_fonts(
            fonts_unsorted,
            args.alternate_italics,
            args.debug
        )
        print(f'{"unsorted":<36} sorted')
        for left, right in zip(fonts_unsorted, fonts_sorted):
            print(f'{get_ps_name(left):<36} {get_ps_name(right)}')


if __name__ == '__main__':
    main()
