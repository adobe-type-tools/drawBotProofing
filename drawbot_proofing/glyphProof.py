# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates a PDF document which helps comparing glyphs to each other.
Various modes are possible – the default is an
[Autopsy](https://vimeo.com/116063612)-like showing of glyphs in a grid view.
Other modes include
* `gradient` (horizontal waterfall)
* `single` (page-by-page)
* `overlay` (superimposed outline view)

Input (pick one):
* folder(s) containing UFO files or font files
* individual UFO- or font files
* designspace file (UFO sources)

In the input filtering process, UFO files are preferred to fonts, OTFs to TTFs.
If results are unexpected, it helps to specify input files one-by-one.

'''

import math
import re

import argparse
import colorsys
import random
import subprocess

import defcon
import drawBot as db

from fontTools import ttLib
from pathlib import Path

from .proofing_helpers import fontSorter
from .proofing_helpers.drawing import draw_glyph
from .proofing_helpers.files import get_ufo_paths, get_font_paths
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.stamps import timestamp
from .proofing_helpers.names import get_name_overlap


# general measurements
BOX_WIDTH = 200
BOX_HEIGHT = BOX_WIDTH * 1.5
MARGIN = BOX_HEIGHT * 0.1


class FontContainer(object):
    '''
    an object that contains
    * the font object (defcon or fontTools)
    * a reference to the original file
    * the object’s flavor
    * a container dict for glyph access
    '''

    def __init__(self, font_file):
        self.font = self.make_font_object(font_file)
        self.file = font_file
        self.flavor = self.get_flavor(self.font)
        self.container = self.get_container(self.font)

    def make_font_object(self, font_file):
        if font_file.suffix.lower() == '.ufo':
            font_obj = defcon.Font(font_file)
        else:
            # font files
            font_obj = ttLib.TTFont(font_file)
        return font_obj

    def get_container(self, font_obj):
        '''
        get the container dict to access glyph objects
        '''
        if isinstance(font_obj, defcon.Font):
            container = font_obj
        else:
            container = font_obj.getGlyphSet()
        return container

    def get_flavor(self, font_obj):
        if isinstance(font_obj, defcon.Font):
            flavor = 'dc_font'
        else:
            flavor = 'tt_font'
        return flavor


class ProofingFont(FontContainer):

    '''
    an object that contains everything FontContainer contains, plus
    * style name
    * family name
    * glyph order
    * UPM
    * glyph name-to-codepoint dict
    * glyph name-to-anchors dict
    '''

    def __init__(self, font_file):
        FontContainer.__init__(self, font_file)
        self.style_name = self.get_style_name(self.font)
        self.family_name = self.get_family_name(self.font)
        self.glyph_order = self.get_glyph_order(self.font)
        self.upm = self.get_upm(self.font)

        self.uni_dict = self.make_uni_dict(self.font)
        self.anchor_dict = self.make_anchor_dict(self.font)

    def get_style_name(self, f):
        if self.flavor == 'dc_font':
            style_name = f.info.styleName
        else:
            name_table = f['name']
            style_name = name_table.getDebugName(17)
            if not style_name:
                style_name = name_table.getDebugName(2)

        if not style_name:
            style_name = '[no style name]'

        return style_name

    def get_family_name(self, f):
        if self.flavor == 'dc_font':
            family_name = f.info.familyName
        else:
            name_table = f['name']
            family_name = name_table.getDebugName(16)
            if not family_name:
                family_name = name_table.getDebugName(1)

        if not family_name:
            family_name = '[no family name]'

        return family_name

    def get_glyph_order(self, f):
        '''
        for a UFO:
            return a list of glyph names
            - ordered by glyphOrder, or (if glyphOrder does not exist)
              ordered by unicodeData.sortGlyphNames
            - existing in the font object
        for a fontTools TTFont:
            return the inherent glyphOrder
        '''

        if self.flavor == 'dc_font':
            keys = f.keys()
            glyph_order = f.glyphOrder
            if not glyph_order:
                glyph_order = f.unicodeData.sortGlyphNames(keys)
            return sorted(keys, key=glyph_order.index)

        else:
            # fontTools font
            # the `list` wrapper is deliberate.
            # If we just return the getGlyphOrder object it is possible to
            # accidentally modify it in memory
            return list(f.getGlyphOrder())

    def get_upm(self, f):
        if self.flavor == 'dc_font':
            upm = f.info.unitsPerEm
        else:
            upm = f['head'].unitsPerEm

        if not upm:
            upm = 1000

        return upm

    def make_uni_dict(self, f):
        '''
        { glyph name: code point dict }
        xxx double-mapping is ignored, not really relevant for this use case
        '''
        if self.flavor == 'dc_font':
            gn_2_cp = {g.name: g.unicode for g in f if g.unicode}
        else:
            reverse_cmap = f['cmap'].buildReversed()
            gn_2_cp = {gn: list(cp)[0] for gn, cp in reverse_cmap.items()}

        return gn_2_cp

    def make_anchor_dict(self, f):
        '''
        collect all anchors and their coordinates
        xxx at the moment, anchors for cursive attachment are not collected.
        '''
        anchor_dict = {}

        if self.flavor == 'dc_font':
            for g in f:
                for anchor in g.anchors:
                    coords = anchor.x, anchor.y
                    anchor_dict.setdefault(g.name, []).append(coords)
        else:
            if not ('GPOS' in f):
                return {}

            # lu_types = [4, 5, 6]
            lookups = f['GPOS'].table.LookupList.Lookup

            # mark-to-base
            m2b_lookups = [lu for lu in lookups if lu.LookupType == 4]
            for lu in m2b_lookups:
                # MarkBasePos
                for mbp in lu.SubTable:
                    base_glyphs = mbp.BaseCoverage.glyphs
                    mark_glyphs = mbp.MarkCoverage.glyphs
                    for mi, mr in enumerate(mbp.MarkArray.MarkRecord):
                        glyph = mark_glyphs[mi]
                        anchor = mr.MarkAnchor
                        coords = anchor.XCoordinate, anchor.YCoordinate
                        anchor_dict.setdefault(glyph, []).append(coords)

                    for bi, br in enumerate(mbp.BaseArray.BaseRecord):
                        glyph = base_glyphs[bi]
                        for anchor in br.BaseAnchor:
                            coords = anchor.XCoordinate, anchor.YCoordinate
                            anchor_dict.setdefault(glyph, []).append(coords)

            # mark-to-ligature
            m2l_lookups = [lu for lu in lookups if lu.LookupType == 5]
            for lu in m2l_lookups:
                # MarkLigPos
                for mlp in lu.SubTable:
                    liga_glyphs = mlp.LigatureCoverage.glyphs
                    mark_glyphs = mlp.MarkCoverage.glyphs
                    for mi, mr in enumerate(mlp.MarkArray.MarkRecord):
                        glyph = mark_glyphs[mi]
                        anchor = mr.MarkAnchor
                        coords = anchor.XCoordinate, anchor.YCoordinate
                        anchor_dict.setdefault(glyph, []).append(coords)

                    for li, la in enumerate(mlp.LigatureArray.LigatureAttach):
                        glyph = liga_glyphs[li]
                        for cr in la.ComponentRecord:
                            for anchor in cr.LigatureAnchor:
                                coords = anchor.XCoordinate, anchor.YCoordinate
                                anchor_dict.setdefault(glyph, []).append(coords)

            # mark-to-mark
            m2m_lookups = [lu for lu in lookups if lu.LookupType == 6]
            for lu in m2m_lookups:
                # MarkMarkPos
                for mmp in lu.SubTable:
                    mark1_glyphs = mmp.Mark1Coverage.glyphs
                    mark2_glyphs = mmp.Mark2Coverage.glyphs
                    for mi, mr in enumerate(mmp.Mark1Array.MarkRecord):
                        glyph = mark1_glyphs[mi]
                        anchor = mr.MarkAnchor
                        coords = anchor.XCoordinate, anchor.YCoordinate
                        anchor_dict.setdefault(glyph, []).append(coords)
                    for mi, mr in enumerate(mmp.Mark2Array.Mark2Record):
                        glyph = mark2_glyphs[mi]
                        for anchor in mr.Mark2Anchor:
                            coords = anchor.XCoordinate, anchor.YCoordinate
                            anchor_dict.setdefault(glyph, []).append(coords)

        return anchor_dict


def draw_anchors(glyph, anchor_coords, size=30):
    radius = size / 2
    for x, y in anchor_coords:
        db.fill(1, 0, 0)
        db.oval(x - radius, y - radius, size, size)


def draw_sidebearings(glyph, height=100):
    # stroke(0.5)
    # strokeWidth(0.5)
    db.line((0, -height / 2), (0, height / 2))
    db.line((glyph.width, -height / 2), (glyph.width, height / 2))


def calc_vector(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return x2 - x1, y2 - y1


def calc_distance(p1, p2):
    return math.hypot(*calc_vector(p1, p2))


def calc_angle(p1, p2):
    dx, dy = calc_vector(p1, p2)
    return math.atan2(dy, dx)


def polar_point(center, radius, angle):
    '''
    Get points on a circle for arbitrary angle
    '''
    x = center[0] + radius * math.cos(angle)
    y = center[1] + radius * math.sin(angle)
    return x, y


def get_bounds(g):
    '''
    find out if a glyph has contours or not
    '''
    if isinstance(g, defcon.Glyph):
        bounds = g.bounds
    else:
        from fontTools.pens.boundsPen import BoundsPen
        bp = BoundsPen(g.glyphSet)
        g.draw(bp)
        bounds = bp.bounds
    return bounds


def get_cover_font_and_glyph(proofing_fonts):
    '''
    Gets a random glyph (with outlines) to display on cover
    Also, the ProofingFont object this glyph comes from
    '''
    random_pf = db.choice(proofing_fonts)
    random_gname = db.choice(random_pf.glyph_order)
    glyph = random_pf.container[random_gname]
    bounds = get_bounds(glyph)
    if not bounds:
        _, glyph = get_cover_font_and_glyph(proofing_fonts)

    return random_pf, glyph


def get_global_family_name(proofing_fonts):

    family_names = [pf.family_name for pf in proofing_fonts]
    unique_family_names = sorted(set(family_names), key=family_names.index)
    style_names = [pf.style_name for pf in proofing_fonts]
    overlap = get_name_overlap(unique_family_names)

    if len(unique_family_names) == 1:
        global_fn = unique_family_names[0]

    elif len(unique_family_names) == 2:
        global_fn = ' & '.join(unique_family_names)

    else:
        if overlap and len(overlap) > 3:
            global_fn = overlap
        else:
            global_fn = ', '.join(unique_family_names[:2]) + ' etc.'

    if 'It' not in global_fn and all(['Italic' in sn for sn in style_names]):
        global_fn += ' Italic'

    return global_fn


def get_global_uni_dict(proofing_fonts):
    '''
    all glyphs of all fonts with their code points
    '''
    cmb_uni_dict = {}
    for pf in proofing_fonts:
        cmb_uni_dict.update(pf.uni_dict)

    return cmb_uni_dict


def make_single_glyph_page(glyph_name, pf, page_size, args):
    '''
    A page with a single glyph, intended for a “flip-book” style showing.
    '''

    db.newPage(*page_size)
    scale_factor = 1000 / pf.upm

    if glyph_name in pf.container.keys():
        glyph = pf.container[glyph_name]
        db.fill(0)
    else:
        glyph = pf.container['.notdef']
        db.fill(0, 0, 0, 0.25)

    x_offset = (db.width() - glyph.width * scale_factor) // 2
    y_offset = 250

    footer = db.FormattedString(
        txt=f'{pf.style_name} – {glyph_name}',
        font=FONT_MONO,
        fontSize=20,
        align='center')
    db.textBox(footer, (0, 0, db.width(), 100))

    db.translate(x_offset, y_offset)
    db.scale(scale_factor)
    db.stroke(None)
    draw_glyph(glyph)

    if args.anchors:
        anchors = pf.anchor_dict.get(glyph_name)
        if anchors:
            draw_anchors(glyph, anchors)


def make_overlay_glyph_page(glyph_name, proofing_fonts, stroke_colors, page_size, args):
    '''
    A page with all glyphs of the same name overlaid (in outlines).
    '''
    db.newPage(*page_size)

    for i, pf in enumerate(proofing_fonts):
        stroke_color = stroke_colors[i]
        if glyph_name in pf.container.keys():
            glyph = pf.container[glyph_name]
            scale_factor = 1000 / pf.upm

            with db.savedState():
                x_offset = (db.width() - glyph.width * scale_factor) // 2
                y_offset = 250
                db.translate(x_offset, y_offset)
                db.scale(scale_factor)

                db.fill(None)
                db.stroke(*stroke_color)
                db.strokeWidth(0.25 / scale_factor)
                draw_glyph(glyph)
                db.stroke(None)
                if args.anchors:
                    anchors = pf.anchor_dict.get(glyph_name)
                    if anchors:
                        draw_anchors(glyph, anchors)

    footer = db.FormattedString(
        txt=glyph_name, font=FONT_MONO, fontSize=20, align='center')
    db.textBox(footer, (0, 0, db.width(), 100))


def make_gradient_page(glyph_name, proofing_fonts, page_size):

    # xxx only works for fonts with the same UPM across styles
    page_width, page_height = page_size
    global_scale = BOX_WIDTH / 1000
    db.newPage(*page_size)

    if proofing_fonts[0].flavor == 'dc_font':
        combined_width = sum([
            pf.container[glyph_name].width
            for pf in proofing_fonts if glyph_name in pf.container])
    else:
        hmtx_metrics = [
            pf.font['hmtx'].metrics.get(glyph_name, (0, 0))
            for pf in proofing_fonts if glyph_name in pf.glyph_order]

        # this would take different UPMs into account
        # combined_width = sum([
        #     m[0] * (1000 / proofing_fonts[i].upm)
        #     for i, m in enumerate(hmtx_metrics)])

        combined_width = sum([m[0] for i, m in enumerate(hmtx_metrics)])

    upms = [pf.upm for pf in proofing_fonts]
    upm_factor = 1000 / upms[0]
    # x_offset = (page_width - combined_width * scale_factor) / 2
    x_offset = (page_width - combined_width * global_scale * upm_factor) / 2
    y_offset = 100

    with db.savedState():
        db.translate(x_offset, y_offset)
        db.scale(global_scale * upm_factor)
        for i, pf in enumerate(proofing_fonts):
            if glyph_name in pf.container.keys():
                glyph = pf.container[glyph_name]
                draw_glyph(glyph)
                db.translate(glyph.width, 0)

    footer = db.FormattedString(
        txt=glyph_name, font=FONT_MONO, fontSize=10, align='center')
    db.textBox(footer, (0, 0, page_width, 50))


def make_cover(family_name, proofing_fonts, page_size, margin=20):
    '''
    Make cover with gradient, some info about the family, and a large white
    shape overlaid.
    '''
    page_width, page_height = page_size
    db.newPage(*page_size)
    start_color, end_color = make_gradient_stops()

    db.linearGradient(
        (0, 0),  # startPoint
        (0, page_width),  # endPoint
        [(start_color), (end_color)],  # colors
    )

    db.rect(0, 0, page_width, page_height)
    cover_font, cover_glyph = get_cover_font_and_glyph(proofing_fonts)
    page_center = page_width / 2, page_height / 2

    with db.savedState():
        glyph_bounds = get_bounds(cover_glyph)
        glyph_height = glyph_bounds[3] - glyph_bounds[1]
        glyph_width = glyph_bounds[2] - glyph_bounds[0]
        glyph_center = (
            glyph_bounds[0] + glyph_width / 2,
            glyph_bounds[1] + glyph_height / 2)

        if glyph_height > glyph_width:
            scale_factor = page_height / glyph_height
        else:
            scale_factor = page_height / glyph_width

        scale_factor *= 3

        db.translate(-glyph_center[0], -glyph_center[1])
        db.scale(scale_factor, center=glyph_center)

        h_jiggle = db.randint(int(-page_width / 8), int(page_width / 8))
        v_jiggle = db.randint(int(-page_height / 8), int(page_height / 8))
        db.translate(
            page_center[0] / scale_factor + h_jiggle,
            page_center[1] / scale_factor + v_jiggle,
        )

        db.fill(1)
        draw_glyph(cover_glyph)

        print(f'cover: {cover_glyph.name} ({cover_font.style_name})')

    cover_text = '{}\n{}'.format(
        family_name, timestamp(readable=True, connector='\n'))

    cover_stamp = db.FormattedString(
        txt=cover_text,
        font=FONT_MONO,
        fontSize=10,
        align='left'
    )
    rect_size = (
        margin, page_height - 2 * margin,
        page_width - 2 * margin, margin * 1.5)

    db.fill(0)
    db.textBox(cover_stamp, (rect_size))


def make_proof_page(glyph_name, proofing_fonts, args):
    '''
    Default mode, in which glyphs are set side-by-side.
    '''
    rows, columns = get_rows_columns(len(proofing_fonts), args)

    page_width = BOX_WIDTH * columns
    page_height = BOX_HEIGHT * rows

    uni_dict = get_global_uni_dict(proofing_fonts)
    num_glyphs = 0
    current_line = 1

    # see if the glyph exists in at least one of the fonts
    glyph_exists = [glyph_name in pf.container for pf in proofing_fonts]
    if any(glyph_exists):

        db.newPage(page_width, page_height)
        db.stroke(0.5)
        db.strokeWidth(0.5)

        for i in range(1, rows + 1):
            y_offset = page_height - (BOX_HEIGHT * i) + BOX_WIDTH * 0.4
            db.line((0, y_offset), (page_width, y_offset))

        unicode_value = uni_dict.get(glyph_name)
        if unicode_value:
            char = chr(unicode_value)
            stamp_text = f'{glyph_name} | {char} | U+{unicode_value:04X}'
        else:
            stamp_text = glyph_name

        header = db.FormattedString(
            txt=stamp_text,
            font=FONT_MONO,
            fontSize=10,
            align='center'
        )

        rect_size = (
            MARGIN, page_height - MARGIN, page_width - 2 * MARGIN, MARGIN / 2)
        db.fill(None)
        db.textBox(header, (rect_size))
        x_offset = 0
        page_anchors = {}
        max_anchors_per_line = columns

        for pf in proofing_fonts:
            num_glyphs += 1
            db.fill(0)
            y_offset = page_height - (BOX_HEIGHT * current_line) + BOX_WIDTH * 0.4

            if glyph_name in pf.container:
                db.fill(0)
                glyph = pf.container[glyph_name]
                draw_sb = True

            else:
                db.fill(0.8)
                if '.notdef' in pf.container:
                    glyph = pf.container['.notdef']
                elif 'space' in pf.container:
                    glyph = pf.container['space']
                else:
                    gname = pf.glyph_order[0]
                    glyph = pf.container[gname]

                draw_sb = False
                max_anchors_per_line -= 1

            with db.savedState():

                scale_factor = BOX_WIDTH / pf.upm
                local_offset = (BOX_WIDTH - glyph.width * scale_factor) // 2
                db.translate(x_offset + local_offset, y_offset)
                db.scale(scale_factor)

                if draw_sb:
                    draw_sidebearings(glyph)

                db.stroke(None)
                draw_glyph(glyph)

                if args.anchors:
                    anchors = pf.anchor_dict.get(glyph_name)
                    if anchors:
                        for anchor_index, anchor_coords in enumerate(anchors):
                            x, y = anchor_coords
                            an_x = x * scale_factor + x_offset + local_offset
                            an_y = y * scale_factor + y_offset
                            page_anchors.setdefault(
                                anchor_index, []).append((an_x, an_y))
                        draw_anchors(glyph, anchors)

            x_offset += BOX_WIDTH
            if num_glyphs % columns == 0:
                current_line += 1
                x_offset = 0

        if args.anchors:
            for anchor_index, anchor_list in page_anchors.items():
                db.strokeWidth(0.5)
                hue = random.choice(range(256)) / 256
                stroke_color = colorsys.hls_to_rgb(hue, 0.5, 1)
                db.stroke(*stroke_color)
                db.fill(None)
                for c_index, coord_pair in enumerate(anchor_list):

                    if c_index == 0:
                        db.newPath()
                        db.moveTo(coord_pair)
                        previous_pair = coord_pair
                    elif c_index % max_anchors_per_line == 0:
                        db.newPath()
                        db.moveTo(anchor_list[c_index])
                        previous_pair = anchor_list[c_index]
                    else:
                        pt_distance = calc_distance(previous_pair, coord_pair)
                        pt_angle = calc_angle(previous_pair, coord_pair)
                        pt_center = polar_point(
                            previous_pair, pt_distance / 2, pt_angle)
                        pt_center_offset = polar_point(
                            pt_center, 50, - math.pi / 2)
                        db.qCurveTo(pt_center_offset, coord_pair)
                        previous_pair = coord_pair
                    db.drawPath()


def get_rows_columns(num_fonts, args):
    # column calculation based on number of fonts provided
    if args.columns:
        # column number has been overridden manually
        columns = args.columns

    else:
        if num_fonts <= 5:
            columns = num_fonts
        else:
            if 6 <= num_fonts < 10:
                columns = num_fonts // 2
            else:
                columns = math.ceil(math.sqrt(num_fonts))

    rows = math.ceil(num_fonts) // columns

    return rows, columns


def compress_user(path):
    '''
    opposite of .expanduser()
    '''
    user_folder = str(Path('~').expanduser())
    return str(path).replace(user_folder, '~')


def make_output_path(family_name, output_mode, matches=[]):
    '''
    Make output path based on the options chosen.
    '''
    if family_name is None:
        family_name = 'no family name'
    name_chunks = [output_mode, family_name]

    if matches:
        rep_start = matches[0]
        rep_end = matches[-1]

        if rep_start != rep_end:
            name_chunks.append(f'({rep_start} to {rep_end})')
        else:
            name_chunks.append(f'({rep_start})')

    output_name = ' '.join(name_chunks) + '.pdf'
    output_path = Path(f'~/Desktop/{output_name}').expanduser()

    return output_path


def filter_glyph_names(glyph_names, regex_str):
    '''
    filter a list of glyphs by regular expression
    '''
    matches = None
    reg_ex = re.compile(regex_str)
    matches = list(filter(reg_ex.match, glyph_names))
    if matches:
        print('filtered glyph list:')
        print(' '.join(matches))
        return matches
    else:
        print('no matches for regular expression')
        return glyph_names


def get_glyph_names(proofing_fonts, contours=False):
    '''
    get glyph names -- either all, or only names for glyphs with contours
    '''
    glyph_names = []
    template_font = proofing_fonts[0]
    template_gnames = template_font.glyph_order

    if contours:
        # only contours, no empty or composite glyphs
        glyph_names = [
            gn for gn in template_gnames if len(template_font[gn])]

        for pf in proofing_fonts[1:]:
            addl_glyph_names = [
                gn for gn in pf.glyph_order if
                len(pf.font[gn]) and gn not in glyph_names
            ]
            glyph_names.extend(addl_glyph_names)

    else:
        # all glyphs, including space etc.
        glyph_names = template_gnames
        for pf in proofing_fonts[1:]:
            addl_glyph_names = [
                gn for gn in pf.glyph_order if
                gn not in glyph_names
            ]
            glyph_names.extend(addl_glyph_names)
    return glyph_names


def build_proofing_fonts(input_paths):
    '''
    * if UFOs are found, return a list of defcon Font objects
    * if fonts are found, return a list of ttFont objects
    '''

    if len(input_paths) == 1:
        ufo_paths = get_ufo_paths(input_paths[0])
        font_paths = get_font_paths(input_paths[0])

        if ufo_paths:
            input_files = fontSorter.sort_fonts(ufo_paths)
        elif font_paths:
            input_files = fontSorter.sort_fonts(font_paths)
        else:
            input_files = []
    else:
        # no sorting, just passing single files
        input_files = [Path(p) for p in input_paths]

    proofing_fonts = list(map(ProofingFont, input_files))
    return proofing_fonts


def make_gradient_stops():
    '''
    Returns two gradient color values
    '''
    saturation = 1
    luminance = 0.5
    gamut = 48
    hue_number = db.randint(0, 256)
    next_hue_number = (hue_number + gamut) % 256
    hue = hue_number / 256
    next_hue = next_hue_number / 256

    start_color = colorsys.hls_to_rgb(hue, luminance, saturation)
    end_color = colorsys.hls_to_rgb(next_hue, luminance, saturation)
    return start_color, end_color


def make_stroke_colors(font_list, args):
    if args.stroke_colors:
        # strokes are colorful
        stroke_colors = []
        for font in font_list:
            hue = random.choice(range(256)) / 255
            stroke_colors.append(colorsys.hls_to_rgb(hue, 0.5, 1))
    else:
        # all strokes are black
        stroke_colors = [(0, 0, 0, 1) for f in font_list]

    return stroke_colors


def get_options(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter
    )

    parser.add_argument(
        '-a', '--anchors',
        default=False,
        action='store_true',
        help='draw anchors')

    parser.add_argument(
        '-c', '--contours',
        default=False,
        action='store_true',
        help='only draw glyphs with contours')

    parser.add_argument(
        '-r', '--regex',
        action='store',
        metavar='REGEX',
        type=str,
        help='regular expression to filter glyph list')

    parser.add_argument(
        '-m', '--mode',
        choices=['single', 'overlay', 'gradient'],
        default='default',
        required=False,
        help='alternate output modes')

    parser.add_argument(
        '-s', '--stroke_colors',
        action='store_true',
        default=False,
        help='color strokes in overlay mode')

    parser.add_argument(
        '-l', '--columns',
        required=False,
        type=int,
        help='override automatic number of columns'
    )
    parser.add_argument(
        'd',
        action='store',
        metavar='FOLDER',
        nargs='+',
        help='folder to crawl')

    return parser.parse_args(args)


def make_proof(proofing_fonts, args):

    glyph_list = get_glyph_names(proofing_fonts, args.contours)
    if args.regex:
        glyph_list = filter_glyph_names(glyph_list, args.regex)

    global_family_name = get_global_family_name(proofing_fonts)
    db.newDrawing()

    if args.mode == 'single':
        page_size = (1200, 1200)
        output_mode = 'page proof'
        if len(glyph_list) > 1:
            # do not make a cover for a single-page proof
            make_cover(global_family_name, proofing_fonts, page_size, MARGIN)
        for glyph_name in glyph_list:
            for pf in proofing_fonts:
                make_single_glyph_page(glyph_name, pf, page_size, args)

    elif args.mode == 'overlay':
        page_size = (1200, 1200)
        output_mode = 'overlay proof'
        stroke_colors = make_stroke_colors(proofing_fonts, args)
        if len(glyph_list) > 1:
            make_cover(global_family_name, proofing_fonts, page_size, MARGIN)

        for glyph_name in glyph_list:
            make_overlay_glyph_page(
                glyph_name, proofing_fonts, stroke_colors, page_size, args)

    elif args.mode == 'gradient':
        page_size = BOX_WIDTH * len(proofing_fonts), BOX_HEIGHT
        output_mode = 'gradient proof'
        if len(glyph_list) > 1:
            make_cover(global_family_name, proofing_fonts, page_size, MARGIN)
        for glyph_name in glyph_list:
            make_gradient_page(glyph_name, proofing_fonts, page_size)

    else:
        # default
        output_mode = 'glyph proof'
        rows, columns = get_rows_columns(len(proofing_fonts), args)
        page_size = (BOX_WIDTH * columns, BOX_HEIGHT * rows)

        if len(glyph_list) > 1:
            make_cover(global_family_name, proofing_fonts, page_size, MARGIN)
        for glyph_name in glyph_list:
            make_proof_page(glyph_name, proofing_fonts, args)

    if args.regex:
        output_path = make_output_path(
            global_family_name, output_mode, glyph_list)
    else:
        output_path = make_output_path(global_family_name, output_mode)

    db.saveImage(output_path)
    print('saved PDF to', compress_user(output_path))
    subprocess.call(['open', output_path])
    db.endDrawing()


def main(test_args=None):
    args = get_options(test_args)
    proofing_fonts = build_proofing_fonts(args.d)
    if proofing_fonts:
        for pf in proofing_fonts:
            print(pf.family_name, pf.style_name)
        make_proof(proofing_fonts, args)
    else:
        print(f'no fonts or UFOs found in {args.d}')


if __name__ == '__main__':
    main()
