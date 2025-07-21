# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import os
import sys

mod_dir = os.path.join(os.path.dirname(__file__), '..')
if mod_dir not in sys.path:
    sys.path.append(mod_dir)

from proofing_helpers.charsets import *
from proofing_helpers.files import chain_charset_texts
from proofing_helpers.helpers import list_uni_names


cyr_addl_codepoints = [
    # these combining accents occur in Cyrillic texts, but are not officially
    # part of AC-charsets.
    0x0300,  # cmb grave
    0x0301,  # cmb acute
]

space_codepoints = [
    # spaces and control characters
    0x000A,  # space
    0x200B,  # zw space
    0x2009,  # thin space
]


cyr_addl_chars = ''.join([chr(i) for i in cyr_addl_codepoints])
space_chars = ''.join([chr(i) for i in space_codepoints])


def get_dbl_mapped_for_charset(charset):

    dbl_mapped_codepoints = [
        # these codepoints may be double-mapped
        (0x0020, 0x00A0),  # SPACE | NO-BREAK SPACE
        (0x0060, 0x02CB),  # GRAVE ACCENT | MODIFIER LETTER GRAVE ACCENT
        (0x00B4, 0x02CA),  # ACUTE ACCENT | MODIFIER LETTER ACUTE ACCENT
        (0x00AF, 0x02C9),  # MACRON | MODIFIER LETTER MACRON
        (0x0394, 0x2206),  # GREEK CAPITAL LETTER DELTA | INCREMENT
        (0x03A9, 0x2126),  # GREEK CAPITAL LETTER OMEGA | OHM SIGN
        (0x03BC, 0x00B5),  # GREEK SMALL LETTER MU | MICRO SIGN
        (0x2018, 0x02BB),  # LEFT SINGLE QUOTATION MARK | MODIFIER LETTER TURNED COMMA
        (0x2019, 0x02BC),  # RIGHT SINGLE QUOTATION MARK | MODIFIER LETTER APOSTROPHE
        (0x2044, 0x2215),  # FRACTION SLASH | DIVISION SLASH
        (0x002D, 0x00AD, 0x2010),  # HYPHEN-MINUS | SOFT HYPHEN | HYPHEN
        (0x00B7, 0x2219),  # MIDDLE DOT | BULLET OPERATOR
        (0x003B, 0x037E),  # SEMICOLON | GREEK QUESTION MARK
    ]
    dbl_mapped_in_this_charset = set()
    for cluster in dbl_mapped_codepoints:
        db_mapped_chars = [chr(i) for i in cluster]
        if set(db_mapped_chars) & charset:
            dbl_mapped_in_this_charset.update(set(db_mapped_chars))
    return dbl_mapped_in_this_charset


def filter_by_charset(charset, content):
    contained = []
    exceeding = []
    for line in content:
        if len(line.strip()):
            if set(line) <= set(charset):
                contained.append(line)
            else:
                exceeding.append(line)
    return contained, exceeding


def categorize_lines(cs_prefix, cs_index=5):
    raw_content = chain_charset_texts(cs_prefix, cs_index)
    content_list = list(set(raw_content.split('\n')))
    content_dir = os.path.dirname(__file__)
    exceeding = content_list
    for i in range(cs_index + 1):
        if i == 0:
            charset_name = 'ascii'
        else:
            charset_name = f'{cs_prefix.lower()}{i}'
        cs_file = os.path.join(content_dir, charset_name.upper() + '.txt')
        charset = set(eval(charset_name))
        charset.update(set(space_chars))

        if cs_prefix == 'AC':
            charset = set(charset) | set(al1) | set(cyr_addl_chars)
        elif cs_prefix == 'AG':
            charset = set(charset) | set(al1)

        dbl_mapped_in_this_charset = get_dbl_mapped_for_charset(charset)
        charset.update(dbl_mapped_in_this_charset)
        contained, exceeding = filter_by_charset(charset, exceeding)

        with open(cs_file, 'w') as f:
            f.write('\n'.join(sorted(contained)) + '\n')

    if exceeding:
        # This will potentially write duplicate lines, but probably
        # it’s not very urgent to fix this.
        # They will be de-duplicated if added to one of the source text files.
        print(
            f'lines exceeding largest {cs_prefix} charset '
            f'({cs_prefix}{cs_index}):')
        for line in exceeding:
            print(line)
            beyond = set(line) - set(charset)
            list_uni_names(sorted(beyond))
            print()
        ex_file = os.path.join(
            content_dir, 'beyond_' + charset_name.upper() + '.txt')
        if os.path.exists(ex_file):
            # append to existing file
            write_mode = 'a'
        else:
            write_mode = 'w'
        with open(ex_file, write_mode) as f:
            f.write('\n'.join(sorted(exceeding)) + '\n')


def check_text_file(cs_prefix, cs_index=5):
    if cs_index == 0:
        charset_name = 'ascii'
    else:
        charset_name = f'{cs_prefix.lower()}{cs_index}'

    charset_file_name = charset_name.upper() + '.txt'
    charset = set(eval(charset_name.lower()))  # | set(space_chars)

    raw_content = chain_charset_texts(cs_prefix, cs_index)

    if cs_index == 0:
        all_chars = set(charset) | set(space_chars)

    else:
        # AL1 is added to every charset but ASCII since it can be expected
        # for Greek and Cyrillic texts to contain Latin letters.
        all_chars = set(charset) | set(al1) | set(cyr_addl_chars) | set(space_chars)

    # take care of double-mapping
    dbl_mapped_in_this_charset = get_dbl_mapped_for_charset(all_chars)
    all_chars.update(dbl_mapped_in_this_charset)
    missing = set(charset) - set(raw_content) - dbl_mapped_in_this_charset

    if missing:
        print(
            'Characters missing from source text '
            f'{charset_file_name} ({len(missing)}):'
        )
        list_uni_names(sorted(missing))
        print()
    else:
        print(
            f'Source text {charset_file_name} supports all of {charset_name}.')
        print()


def content_stats(cs_prefix, cs_index, show_max=3):
    '''
    Show list of characters with low occurrence.
    '''
    raw_content = chain_charset_texts(cs_prefix, cs_index)
    content_list = raw_content.split('\n')
    content_dict = {}
    for line in content_list:
        for char in line:
            content_dict.setdefault(char, 0)
            content_dict[char] += 1
    occurence = {}
    for character, count in sorted(
        content_dict.items(),
        key=lambda item: item[1],
    ):

        occurence.setdefault(count, []).append(character)
    if show_max is None:
        show_max = len(occurence)
    for count, charlist in sorted(occurence.items(), reverse=True)[-show_max:]:
        print(f'\t{count}: {"".join(sorted(charlist))} ({len(charlist)})')
    print()


if __name__ == '__main__':

    max_charset_depth = [
        ('AL', 5),
        ('AC', 3),
        ('AG', 2),
    ]

    for cs_tag, cs_level in max_charset_depth:
        categorize_lines(cs_tag, cs_level)
        for i in range(cs_level + 1):
            check_text_file(cs_tag, i)
        print('low occurrence:')
        content_stats(cs_tag, cs_level)
