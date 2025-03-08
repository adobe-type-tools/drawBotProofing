# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import tempfile
import os
from fontTools import ttLib
from pathlib import Path


def get_temp_file_path(extension=None):
    file_descriptor, path = tempfile.mkstemp(suffix=extension)
    os.close(file_descriptor)
    return path


def make_temp_font(file_index, font_file):
    '''
    Make a temporary font file with unique PS name, because the same PS name
    implies that the same font outlines will be seen throughout the PDF.
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
