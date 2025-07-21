# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import defcon
import drawBot as db
from fontParts import fontshell
from fontTools.pens.cocoaPen import CocoaPen


def draw_glyph(glyph):
    '''
    global drawing method, which allows passing either UFO- or fontTools glyphs
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
    db.drawPath(cpen.path)
