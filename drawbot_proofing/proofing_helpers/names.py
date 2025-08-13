# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import plistlib
from fontTools import ttLib


def get_ps_name(input_file):
    '''
    Return the PS name for a font or UFO.
    If the UFO PS name is not filled in, synthesize it.
    '''
    if input_file.suffix == '.ufo':

        fontinfo_path = input_file.joinpath('fontinfo.plist')
        with open(fontinfo_path, 'rb') as fi_blob:
            fi_dict = plistlib.load(fi_blob)

        ps_name = fi_dict.get('postscriptFontName', None)
        if not ps_name:
            family_name = fi_dict.get('familyName', 'Family Name')
            style_name = fi_dict.get('styleName', 'Style Name')
            ps_name = '-'.join([
                family_name.replace(' ', ''),
                style_name.replace(' ', '')
            ])

    else:
        ttf = ttLib.TTFont(input_file.resolve())
        name_table = ttf.get('name')
        ps_name = name_table.getDebugName(6)
        if not ps_name:
            ps_name = ''

    return ps_name


def get_overlap_index(list_of_strings, start_char=0):
    '''
    For a list of strings, find the index at which they stop overlapping.
    '''
    if not list_of_strings:
        return 0
    strings = set(list_of_strings)
    words_by_length = sorted([(len(word), word) for word in strings])
    shortest_word = words_by_length[0][1]

    for i in range(start_char, len(shortest_word)):
        chars = [word[i] for word in list_of_strings]
        if len(set(chars)) > 1:
            # names start to diverge
            return i
        elif i == len(shortest_word) - 1:
            # shortest name is contained in all other names
            return len(shortest_word)
        else:
            continue


def get_name_overlap(list_of_strings):
    '''
    From a list of font names, return the shared bit.
    Remove trailing dashes (PS names are assumed).
    For example:

    SourceSans3-Regular
    SourceSans3-Bold

    -->

    SourceSans3
    '''
    overlap_index = get_overlap_index(list_of_strings)
    return list_of_strings[0][:overlap_index].strip('-')


def get_path_overlap(list_of_paths):
    '''
    from a list of pathlib.paths, return the name of the shared parent folder
    '''

    all_parents = [list(reversed(p.parents)) for p in list_of_paths]
    shortest_parent = min([len(pl) for pl in all_parents])
    for i in range(shortest_parent):
        current_parents = [pl[i] for pl in all_parents]
        if len(set(current_parents)) == 1:
            shared_parent = current_parents[0]
        else:
            break

    if shared_parent == '/':  # root
        return 'various'
    return shared_parent.name
