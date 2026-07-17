# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.


def get_glyph_order(f):
    lib_glyph_order = f.glyphOrder
    all_glyphs = f.keys()

    if set(lib_glyph_order) == set(all_glyphs):
        glyph_order = lib_glyph_order

    else:
        # public.glyphOrder is not mandatory, there could be additional cases:
        # - f.keys() only (in case public.glyphOrder is empty)
        # - additional glyphs not mentioned in public.glyphOrder
        # - ufo template glyhphs (in public.glyphOrder, but not in f.keys())
        additional_glyphs = set(all_glyphs) - set(lib_glyph_order)
        missing_glyphs = set(lib_glyph_order) - set(all_glyphs)
        order = list(lib_glyph_order) + sorted(additional_glyphs)
        glyph_order = [gn for gn in order if gn not in missing_glyphs]
    return glyph_order
