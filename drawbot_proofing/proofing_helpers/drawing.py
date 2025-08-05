# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import defcon
import drawBot as db
from fontParts import fontshell
from fontTools.pens.cocoaPen import CocoaPen


def get_glyph_path(glyph):
    '''
    global path retrieval method,
    which allows passing either UFO- or fontTools glyphs
    '''
    if isinstance(
        glyph, (defcon.objects.glyph.Glyph, fontshell.glyph.RGlyph)
    ):
        # UFO
        cpen = CocoaPen(glyph.getParent())
    else:
        # font
        cpen = CocoaPen(glyph.glyphSet)
    glyph.draw(cpen)

    return cpen.path


def draw_glyph(glyph):
    path = get_glyph_path(glyph)
    db.drawPath(path)
