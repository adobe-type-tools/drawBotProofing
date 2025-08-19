# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

from fontTools import ttLib
from pathlib import Path
from .files import get_temp_file_path


def make_temp_font(file_index, font_file):
    '''
    Make a temporary font file with a unique PS name, so two versions of the
    same design can be embedded into the same PDF.
    If PS names clash, the implication is that the same font outlines will be
    seen throughout the whole document.
    '''
    font = ttLib.TTFont(font_file)
    file_extension = '.otf' if font.sfntVersion == 'OTTO' else '.ttf'
    tmp_font_file = get_temp_file_path(file_extension)
    tmp_ps_name = f'{Path(font_file).stem}_{file_index}'
    for name_entry in font['name'].names:
        if name_entry.nameID == 6:
            font['name'].setName(
                tmp_ps_name,
                nameID=6,
                platformID=name_entry.platformID,
                platEncID=name_entry.platEncID,
                langID=name_entry.langID)
    font.save(tmp_font_file)
    return(tmp_font_file)


def get_default_instance(font_file):
    tf = ttLib.TTFont(font_file)
    fvar = tf.get('fvar', None)
    if fvar:
        instance = {}
        for axis in fvar.axes:
            instance[axis.axisTag] = axis.defaultValue
        return instance

    else:
        return


def supports_charset(cmap, charset):
    cmap_dict = cmap.getBestCmap()
    to_support = set(charset) | set(charset.upper())
    supported_chars = set([chr(cp) for cp in cmap_dict.keys()])
    return to_support <= supported_chars


def supports_lat(cmap):
    return supports_charset(cmap, 'abcdefghijklmnopqrstuvwxyz')


def supports_cyr(cmap):
    return supports_charset(cmap, 'абвгдежзийклмнопрстуфхцчшщъыьэюя')


def supports_grk(cmap):
    return supports_charset(cmap, 'αβγδεζηθικλμνξοπρστυφχψως')


def supports_text(font_file, text, min_percentage=80):
    ttFont = ttLib.TTFont(font_file)
    cmap_dict = ttFont['cmap'].getBestCmap()
    to_support = set(text)
    supported_chars = set([chr(cp) for cp in cmap_dict.keys()])
    leftover = to_support - supported_chars
    support_percentage = (1 - (len(leftover) / len(to_support))) * 100
    if support_percentage > min_percentage:
        return True
    return False
