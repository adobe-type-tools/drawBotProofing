# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import os
import tempfile

from fontTools import ttLib
from pathlib import Path


def get_font_paths(input_path):
    '''
    Search for font files.

    If the path is a directory, all fonts within will be returned.
    OTF files are preferred over TTF files, which are only
    returned if no OTFs are found.

    If the path is a single file, it will be returned
    (given it is an OTF or TTF).

    '''
    otf_paths = []
    ttf_paths = []

    path = Path(input_path).resolve()

    if path.is_dir():
        # directory was passed
        otf_paths = list(path.rglob('*.otf'))
        ttf_paths = list(path.rglob('*.ttf'))
    else:
        # single file was passed
        if path.suffix in ['.otf', '.ttf']:
            return [path]

    if otf_paths:
        return otf_paths
    return ttf_paths


def get_ufo_paths(input_path, filter='font.ufo'):
    '''
    Search for UFO files (font.ufo files are filtered out).
    If a single UFO file is passed, that file will be returned.

    '''
    ufo_paths = []

    path = Path(input_path).resolve()
    if path.is_dir():
        if path.suffix == '.ufo':
            return [path]
        else:
            ufo_paths = list(path.rglob('*.ufo'))
    return ufo_paths


def read_text_file(text_file):
    '''
    Read text file and filter out empty lines and comments.
    Return list of contents.

    '''
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            content = '\n'.join(
                line for line in raw_content.split('\n') if
                line and not line[0] == '#')
        return content

    except FileNotFoundError:
        print(f'file not found: {text_file}')


def chain_charset_texts(cs_prefix='AL', cs_level=3):
    '''
    Read charset example texts, by decreasing the cs_level
    (e.g. AL-3 + AL-2 + AL-1)

    '''
    max_charset_level = int(cs_level)
    raw_content = ''
    content_dir = Path(__file__).parents[1].joinpath('_content')

    for level in (range(max_charset_level, -1, -1)):
        if level == 0:
            if cs_prefix == 'AL':
                text_file_name = f'{content_dir}/ASCII.txt'
            else:
                # do not add ASCII to Cyrillic or Greek
                pass
        else:
            text_file_name = f'{content_dir}/{cs_prefix.upper()}{level}.txt'

        try:
            with open(text_file_name, 'r', encoding='utf-8') as f:
                raw_content += f.read()
        except FileNotFoundError:
            print(f'file not found: {text_file_name}')
            continue
    return raw_content


def get_temp_file_path(extension=None):
    file_descriptor, path = tempfile.mkstemp(suffix=extension)
    os.close(file_descriptor)
    return path


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
