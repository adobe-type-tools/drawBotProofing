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

    return ps_name


def get_overlap_index(list_of_strings, start_char=0):
    '''
    For a list of strings, find the index at which they stop overlapping.
    '''
    if not list_of_strings:
        return 0
    shortest_item_found = min([(len(item), item) for item in list_of_strings])
    shortest_item = shortest_item_found[1]
    for i in range(start_char, len(shortest_item)):
        chars = [item[i] for item in list_of_strings]
        if len(set(chars)) == 1:
            start_char += 1
        else:
            return i


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
