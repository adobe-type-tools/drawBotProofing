# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates PDF document which helps comparing glyphs of different weights
to each other. Various modes are possible – the default is an
[Autopsy](https://vimeo.com/116063612)-like showing of glyphs side-by-side.
Other modes include `gradient`, `single`, `overlay`.

Input: folder with UFO files or individual UFOs

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
from .proofing_helpers.globals import FONT_MONO
from .proofing_helpers.stamps import timestamp
from .proofing_helpers.names import get_name_overlap


# general measurements
BOX_WIDTH = 200
BOX_HEIGHT = BOX_WIDTH * 1.5
margin = BOX_HEIGHT * 0.1


def get_options(args=None):
    parser = argparse.ArgumentParser(
        description=__doc__)

    parser.add_argument(
        '-a', '--anchors',
        default=False,
        action='store_true',
        help='draw anchors')

    # parser.add_argument(
    #     '-m', '--metrics',
    #     default=False,
    #     action='store_true',
    #     help='draw metrics (not implemented)')

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
        '--stroke_colors',
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


def draw_anchors(glyph, size):
    radius = size / 2
    for anchor in glyph.anchors:
        db.fill(1, 0, 0)
        db.oval(anchor.x - radius, anchor.y - radius, size, size)


def draw_sidebearings(glyph, height=100):
    # stroke(0.5)
    # strokeWidth(0.5)
    db.line((0, -height / 2), (0, height / 2))
    db.line((glyph.width, -height / 2), (glyph.width, height / 2))


def draw_metrics(glyph):
    # stroke(0.5)
    # strokeWidth(0.5)
    # font = glyph.font
    font = glyph.getParent()
    db.line((0, font.info.descender), (glyph.width, font.info.descender))
    db.line((0, font.info.xHeight), (glyph.width, font.info.xHeight))
    db.line((0, font.info.capHeight), (glyph.width, font.info.capHeight))
    db.line((0, font.info.ascender), (glyph.width, font.info.ascender))


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


def get_random_glyph(font_list):
    '''
    Gets a random glyph (with outlines) to display on cover
    '''
    random_font = db.choice(font_list)
    random_gname = db.choice(get_glyph_order(random_font))

    if isinstance(random_font, defcon.Font):
        glyph_container = random_font
    else:
        glyph_container = random_font.getGlyphSet()

    glyph = glyph_container[random_gname]
    bounds = get_bounds(glyph)
    if not bounds:
        glyph = get_random_glyph(font_list)

    return glyph


def make_gradient():
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


def make_single_glyph_page(glyph_name, font, page_size, args):
    '''
    A page with a single glyph, intended for a “flip-book” style showing.
    '''

    ufo_name = Path(font.path).name
    if ufo_name == 'font.ufo':
        ufo_name = font.info.postscriptFontName
    stamp = u'%s – %s' % (ufo_name, glyph_name)
    db.newPage(*page_size)
    if glyph_name in font.keys():
        glyph = font[glyph_name]
        db.fill(0)
    else:
        glyph = font['.notdef']
        db.fill(0, 0, 0, 0.25)
    x_offset = (db.width() - glyph.width) // 2
    y_offset = 250

    fs = db.FormattedString(
        txt=stamp, font=FONT_MONO, fontSize=20, align='center')
    db.textBox(fs, (0, 0, db.width(), 100))

    db.translate(x_offset, y_offset)
    db.stroke(None)
    draw_glyph(glyph)
    if args.anchors:
        if glyph.anchors:
            draw_anchors(glyph, 30)


def make_overlay_glyph_page(glyph_name, font_list, stroke_colors, page_size, args):
    '''
    A page with all glyphs of the same name overlaid (in outlines).
    '''
    stamp = u'%s' % glyph_name
    db.newPage(*page_size)

    for i, font in enumerate(font_list):
        stroke_color = stroke_colors[i]
        if glyph_name in font.keys():
            glyph = font[glyph_name]
            with db.savedState():
                db.fill(None)
                db.stroke(*stroke_color)
                db.strokeWidth(0.5)
                x_offset = (db.width() - glyph.width) // 2
                y_offset = 250
                db.translate(x_offset, y_offset)
                draw_glyph(glyph)
                db.stroke(None)
                if args.anchors:
                    if glyph.anchors:
                        draw_anchors(glyph, 30)

    fs = db.FormattedString(
        txt=stamp, font=FONT_MONO, fontSize=20, align='center')
    db.textBox(fs, (0, 0, db.width(), 100))


def get_style_name(f):
    if isinstance(f, defcon.Font):
        style_name = f.info.styleName
        if not style_name:
            style_name = '[no style name]'
    else:
        name_table = f['name']
        style_name = name_table.getDebugName(17)
        if not style_name:
            style_name = name_table.getDebugName(2)

    return style_name


def get_family_name(f):
    if isinstance(f, defcon.Font):
        family_name = f.info.familyName
        if not family_name:
            family_name = '[no family name]'
    else:
        name_table = f['name']
        family_name = name_table.getDebugName(16)
        if not family_name:
            family_name = name_table.getDebugName(1)

    return family_name


def global_family_name(font_list):

    family_names = [get_family_name(f) for f in font_list]
    overlap = get_name_overlap(family_names)

    if overlap and len(overlap) > 3:
        global_fn = overlap
    else:
        global_fn = get_family_name(font_list[0])

    if (
        'It' not in global_fn and
        all(['Italic' in get_style_name(f) for f in font_list])
    ):
        global_fn += ' Italic'

    return global_fn


def make_gradient_page(glyph_name, font_list, page_size):

    page_width, page_height = page_size
    scale_factor = BOX_WIDTH / 1000
    stamp = u'%s' % (glyph_name)
    db.newPage(*page_size)
    combined_width = sum(
        [f[glyph_name].width for f in font_list if glyph_name in f.keys()])
    x_offset = (page_width - combined_width * scale_factor) / 2
    y_offset = 100

    with db.savedState():
        db.translate(x_offset, y_offset)
        db.scale(scale_factor)
        for font in font_list:
            if glyph_name in font.keys():
                glyph = font[glyph_name]
                draw_glyph(glyph)
                db.translate(glyph.width, 0)

    fs = db.FormattedString(
        txt=stamp, font=FONT_MONO, fontSize=10, align='center')
    db.textBox(fs, (0, 0, page_width, 50))


def make_cover(family_name, font_list, page_size, margin=20):
    '''
    Make cover with gradient, some info about the family, and a large white
    shape overlaid.
    '''
    page_width, page_height = page_size
    db.newPage(*page_size)
    start_color, end_color = make_gradient()

    db.linearGradient(
        (0, 0),  # startPoint
        (0, page_width),  # endPoint
        [(start_color), (end_color)],  # colors
    )

    db.rect(0, 0, page_width, page_height)
    cover_glyph = get_random_glyph(font_list)
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

        scale_factor *= 2

        db.translate(-glyph_center[0], -glyph_center[1])
        db.scale(scale_factor, center=glyph_center)

        db.translate(
            page_center[0] / scale_factor + db.randint(-10, 10),
            page_center[1] / scale_factor + db.randint(-10, 10),
        )

        db.fill(1)
        draw_glyph(cover_glyph)

        if isinstance(cover_glyph, defcon.Glyph):
            cg_font = cover_glyph.getParent()
        else:
            cg_font = cover_glyph.glyphSet.font

        cg_style_name = get_style_name(cg_font)
        print(f'cover: {cover_glyph.name} ({cg_style_name})')

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


def make_proof_page(glyph_name, font_list, args):
    '''
    Default mode, in which glyphs are set side-by-side.
    '''
    columns = get_columns(font_list, args)
    rows = math.ceil(len(font_list) / columns)

    page_width = BOX_WIDTH * columns
    page_height = BOX_HEIGHT * rows

    uni_dict = make_uni_dict(font_list)
    num_glyphs = 0
    current_line = 1

    # see if the glyph exists in at least one of the UFOs
    glyph_exists = [glyph_name in font for font in font_list]

    if any(glyph_exists):

        db.newPage(page_width, page_height)
        db.stroke(0.5)
        db.strokeWidth(0.5)

        for i in range(1, rows + 1):
            y_offset = page_height - (BOX_HEIGHT * i) + BOX_WIDTH * 0.4
            db.line((0, y_offset), (page_width, y_offset))

        unicode_value = uni_dict.get(glyph_name)
        if unicode_value:
            stamp_text = u'%s | %s | U+%0.4X' % (
                glyph_name, chr(unicode_value), unicode_value)
        else:
            stamp_text = glyph_name

        stamp = db.FormattedString(
            txt=stamp_text,
            font=FONT_MONO,
            fontSize=10,
            align='center'
        )

        rect_size = (
            margin, page_height - margin,
            page_width - 2 * margin, margin / 2)
        db.fill(None)
        db.textBox(stamp, (rect_size))
        x_offset = 0
        anchor_list = []
        anchor_dict = {}
        max_anchors_per_line = columns
        for font in font_list:
            num_glyphs += 1
            db.fill(0)
            y_offset = page_height - (BOX_HEIGHT * current_line) + BOX_WIDTH * 0.4

            # stylename_stamp = db.FormattedString(
            #     txt=weight_code,
            #     font=FONT_MONO,
            #     fontSize=10,
            #     align='center'
            # )

            if glyph_name in font:
                db.fill(0)
                glyph = font[glyph_name]
                draw_sb = True
                # draw_vm = True

            else:
                db.fill(0.8)
                if '.notdef' in font.keys():
                    glyph = font['.notdef']
                elif 'space' in font.keys():
                    glyph = font['space']
                else:
                    gname = font.glyphOrder[0]
                    glyph = font[gname]
                draw_sb = False
                # draw_vm = False
                max_anchors_per_line -= 1

            with db.savedState():

                scale_factor = BOX_WIDTH / 1000
                local_offset = (BOX_WIDTH - glyph.width * scale_factor) // 2
                db.translate(x_offset + local_offset, y_offset)
                db.scale(scale_factor)

                if draw_sb:
                    draw_sidebearings(glyph)
                # metrics don’t look good
                # if draw_vm:
                #     draw_metrics(glyph)

                db.stroke(None)
                draw_glyph(glyph)

                if args.anchors:
                    if glyph.anchors:
                        for anchor in glyph.anchors:
                            an_x = anchor.x * scale_factor + x_offset + local_offset
                            an_y = anchor.y * scale_factor + y_offset
                            anchor_dict.setdefault(
                                anchor.name, []).append((an_x, an_y))
                        draw_anchors(glyph, 30)

            # if current_line == 1:
            #     textBox(stylename_stamp, (footer_rect))

            x_offset += BOX_WIDTH
            if num_glyphs % columns == 0:
                current_line += 1
                x_offset = 0

        # current_line = 1
        # num_glyphs = 0
        # x_offset = 0

        if args.anchors:
            for anchor_name, anchor_list in anchor_dict.items():
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


def get_columns(font_list, args):
    if args.columns:
        # column number has been overridden manually
        return args.columns

    # calculation based on number of fonts provided
    num_fonts = len(font_list)

    if num_fonts <= 5:
        columns = num_fonts
    else:
        if 6 <= num_fonts < 10:
            columns = num_fonts // 2
        else:
            columns = math.ceil(math.sqrt(num_fonts))

    return columns


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


def compress_user(path):
    '''
    opposite of .expanduser()
    '''
    user_folder = str(Path('~').expanduser())
    return str(path).replace(user_folder, '~')


def get_glyph_order(f):
    '''
    for a Defcon font or fontTools TTFont:
    return a list of glyph names

        - ordered by glyphOrder, or (if glyphOrder does not exist)
          ordered by unicodeData.sortGlyphNames
        - existing in the font object (UFO only)

    '''

    if isinstance(f, defcon.Font):
        # ufo
        keys = f.keys()
        glyph_order = f.glyphOrder
        if not glyph_order:
            glyph_order = f.unicodeData.sortGlyphNames(keys)

        return sorted(keys, key=glyph_order.index)

    else:
        # fontTools font
        return f.getGlyphOrder()


def make_uni_dict(font_list):
    '''
    all glyphs of all fonts with their code points
    '''
    uni_dict = {}
    for font in font_list:
        if isinstance(font, defcon.Font):
            # double-mapping
            reverse_cmap = {g.name: g.unicode for g in font if g.unicode}
        else:
            reverse_cmap = font['cmap'].buildReversed()
        uni_dict.update(reverse_cmap)

    return uni_dict


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


def get_glyph_names(font_list, contours=False):
    '''
    get glyph names -- either all, or only names for glyphs with contours
    '''
    glyph_names = []
    template_font = font_list[0]
    template_gnames = get_glyph_order(template_font)

    if contours:
        # only contours, no empty or composite glyphs
        glyph_names = [
            gn for gn in template_gnames if len(template_font[gn])]

        for font in font_list[1:]:
            addl_glyph_names = [
                gn for gn in get_glyph_order(font) if
                len(font[gn]) and gn not in glyph_names
            ]
            glyph_names.extend(addl_glyph_names)

    else:
        # all glyphs, including space etc.
        glyph_names = template_gnames
        for font in font_list[1:]:
            addl_glyph_names = [
                gn for gn in get_glyph_order(font) if
                gn not in glyph_names
            ]
            glyph_names.extend(addl_glyph_names)

    return glyph_names


def make_font_list(input_args):
    '''
    * if UFOs are found, return a list of defcon Font objects
    * if fonts are found, return a list of ttFont objects
    '''

    if len(input_args) == 1:
        ufo_paths = get_ufo_paths(input_args[0])
        font_paths = get_font_paths(input_args[0])
        ufos = fontSorter.sort_fonts(ufo_paths)
        fonts = fontSorter.sort_fonts(font_paths)

        if ufos:
            input_files = ufos
        elif fonts:
            input_files = fonts
        else:
            input_files = []
    else:
        # no sorting, just passing single files
        input_files = input_args

    suffixes = [file.suffix.lower() for file in input_files]
    if set(suffixes) == {'.ufo'}:
        # ufo files
        font_list = list(map(defcon.Font, input_files))
    else:
        # font files
        font_list = list(map(ttLib.TTFont, input_files))
    return font_list


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


def main(test_args=None):
    args = get_options(test_args)
    font_list = make_font_list(args.d)

    if font_list:
        for font in font_list:
            print(get_style_name(font))
        family_name = global_family_name(font_list)

        glyph_list = get_glyph_names(font_list, args.contours)

        if args.regex:
            glyph_list = filter_glyph_names(glyph_list, args.regex)

        db.newDrawing()

        if args.mode == 'single':
            page_size = (1200, 1200)
            output_mode = 'page proof'
            if len(glyph_list) > 1:
                make_cover(family_name, font_list, page_size, margin)
            for glyph_name in glyph_list:
                for font in font_list:
                    make_single_glyph_page(glyph_name, font, page_size, args)

        elif args.mode == 'overlay':
            page_size = (1200, 1200)
            output_mode = 'overlay proof'
            stroke_colors = make_stroke_colors(font_list, args)
            if len(glyph_list) > 1:
                # do not make a cover for a single-page proof
                make_cover(family_name, font_list, page_size, margin)

            for glyph_name in glyph_list:
                make_overlay_glyph_page(
                    glyph_name, font_list, stroke_colors, page_size, args)

        elif args.mode == 'gradient':
            page_size = BOX_WIDTH * len(font_list), BOX_HEIGHT
            output_mode = 'gradient proof'
            if len(glyph_list) > 1:
                make_cover(family_name, font_list, page_size, margin)
            for glyph_name in glyph_list:
                make_gradient_page(glyph_name, font_list, page_size)

        else:
            # default
            output_mode = 'glyph proof'
            columns = get_columns(font_list, args)
            rows = math.ceil(len(font_list) / columns)
            page_size = (BOX_WIDTH * columns, BOX_HEIGHT * rows)

            if len(glyph_list) > 1:
                make_cover(family_name, font_list, page_size, margin)
            for glyph_name in glyph_list:
                make_proof_page(glyph_name, font_list, args)

        if args.regex:
            output_path = make_output_path(family_name, output_mode, glyph_list)
        else:
            output_path = make_output_path(family_name, output_mode)

        db.saveImage(output_path)
        print('saved PDF to', compress_user(output_path))
        subprocess.call(['open', output_path])
        db.endDrawing()


if __name__ == '__main__':
    main()
