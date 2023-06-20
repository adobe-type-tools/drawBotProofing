# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates character charts similar to the Unicode.org charts for The Unicode
Standard, but using the supplied font (and only the characters present in the
font).

Input: font file or folder containing font files

CLI Inputs: see help

'''

import argparse
from collections import defaultdict
from functools import partial
from math import floor, ceil
from pathlib import Path
import subprocess
import sys

import drawBot as db
from fontTools.ttLib import TTFont
import unicodedataplus

from proofing_helpers.files import get_font_paths
from proofing_helpers.fontSorter import sort_fonts

IN_UI = 'drawBot.ui' in sys.modules

if IN_UI:
    from vanilla.dialogs import getFileOrFolder  # noqa: F401


def get_options(args=None, description=__doc__):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

    parser.add_argument(
        'input_dir',
        action='store',
        metavar='FOLDER',
        help='folder to crawl')

    parser.add_argument(
        '-o', '--output_file_name',
        action='store',
        metavar='PDF',
        help='output file name')

    parser.add_argument(
        '--pagesize',
        choices=["A4", "Letter"],
        default="Letter",
        help="Desired page size")

    parser.add_argument(
        '-v', '--varfont_axes',
        type=_parse_vf_args,
        help="Variable font axis info e.g. 'wght:400,wdth:100'")

    parser.add_argument(
        '-s', '--size',
        type=int,
        default=CHART_FONT_SIZE,
        help="Chart font pointsize override value")

    return parser.parse_args(args)


FONTS_FOLDER = Path(__file__).parent / "_fonts"
BLOCK_TITLE_FONT = FONTS_FOLDER / "SourceSans3-Bold.otf"
BLOCK_TITLE_SIZE = 20
BLOCK_FONTNAME_SIZE = 14

CHART_LABEL_FONT = FONTS_FOLDER / "SourceSans3-Regular.otf"
CHART_LABEL_SIZE = 11

CHART_COL_WIDTH = 32
CHART_ROW_HEIGHT = 42
CHART_ROW_LABEL_Y_OFFSET = 6
CHART_COL_LABEL_Y_OFFSET = -3
CHART_FONT_SIZE = 24
CHART_FONT_BL = CHART_ROW_HEIGHT * 0.52
BLOCK_FONTNAME_Y_OFFSET = 67

CODE_LABEL_FONT = FONTS_FOLDER / "SourceSans3-Light.otf"
CODE_LABEL_SIZE = 7
CODE_LABEL_Y_OFFSET = 11

# line thicknesses
THICK = 1.5
THIN = 0.1


def _parse_vf_args(axisstr):
    vffunc = partial(db.fontVariations)
    for axs in axisstr.split(","):
        ax, axv = axs.split(':')
        vffunc.keywords[ax] = float(axv)

    return vffunc


def get_uni_blocks():
    all_ranges = defaultdict(int)
    for u in range(0, 0x110000):
        uc = chr(u)
        gc = unicodedataplus.category(uc)
        if gc in ('Cc', 'Cn'):  # exclude controls and non-characters
            continue
        block = unicodedataplus.block(uc)
        all_ranges[block] += 1

    return all_ranges


def draw_gauge(x, y, pct, w=25, h=12):
    with db.savedState():
        db.linearGradient(
            startPoint=(x, y),
            endPoint=(x + w, y),
            colors=[[.9, .9, .9], [0, 0, 0]],
            locations=[0, 0.75])
        db.rect(x, y, w, h)
        db.strokeWidth(0)
        db.fill(1)
        wpct = (pct / 100) * w
        db.rect(x + wpct, y, w - wpct, h)
        db.stroke(0)
        db.strokeWidth(0.3)
        db.fill(1, alpha=0)
        db.rect(x, y, w, h)


def make_chart_doc(font_file, args):
    db.newDrawing()

    set_vf = args.varfont_axes or (lambda: None)
    in_font = TTFont(font_file)
    fontname = in_font['name'].getDebugName(4)
    umap = in_font['cmap'].getBestCmap()
    umapset = set(umap)
    uni_blocks = get_uni_blocks()

    # calculate textBox first baseline offset
    db.font(font_file, args.size)
    bls = db.textBoxBaselines(" ", (0, 0, CHART_FONT_SIZE * 2, CHART_FONT_SIZE * 2))
    if len(bls) == 0:
        print(f"Unable to fit font; re-try using the --size option with value < {args.size}.")
        sys.exit(1)
    tbfbo = 0 - bls[0][1]

    NSMARKBASE = db.FormattedString(
        chr(0x25CC),
        font=font_file,
        fallbackFont=FONTS_FOLDER / "SourceCodePro-Regular.otf",
        fontSize=args.size,
        align="center",
        fill=(0.75),
    )

    if 0x25CC in umap:
        NSMARKBASE.font = font_file

    font_blocks = defaultdict(set)

    for u in umap:
        cu = chr(u)
        gc = unicodedataplus.category(cu)
        if gc in ('Cc', 'Cn'):
            continue
        bk = unicodedataplus.block(cu)
        if bk != "No_Block":
            font_blocks[bk].add(u)

    # make index pages -- 64 blocks per page
    for ipg in range(ceil(len(font_blocks)/64)):
        db.newPage(args.pagesize)
        db.linkDestination(f"index{ipg}", (0, db.height()))
        db.fill(0)
        db.font(BLOCK_TITLE_FONT, 20)
        db.textBox(f'{fontname}',
                   (0, db.height() - 60, db.width(), 28),
                   align="center")

    # go through the blocks, break into <= 16 col pages
    for _bki, (blockname, blockcodes) in enumerate(font_blocks.items()):
        blockmin = min(blockcodes)
        blockmax = max(blockcodes)
        block_nmin = (blockmin // 16) * 16
        block_nmax = ((blockmax // 16) * 16) + 15

        for _bpi, blockpagemin in enumerate(range(block_nmin, block_nmax, 16 * 16)):
            # first page of block, make index entry
            pct = len(font_blocks[blockname]) / uni_blocks[blockname] * 100
            if _bpi == 0:
                ipi = floor(_bki / 64)  # which index page
                with db.pages()[ipi]:
                    db.font(CODE_LABEL_FONT, 13)
                    tc = floor((_bki % 64) / 32)
                    tr = _bki % 32
                    cw = db.width() / 2
                    db.text(
                        blockname,
                        (20 + (tc * cw) + 30, db.height() - (tr * 20) - 80))
                    db.linkRect(
                        blockname,
                        (20 + (tc * cw), db.height() - (tr * 20) - 81, cw, 16))
                    draw_gauge(20 + (tc * cw), db.height() - (tr * 20) - 82, pct)

            blockpagemax = min(block_nmax, blockpagemin + 255)

            # if page would be empty, skip
            pageset = set(range(blockpagemin, blockpagemin + 256))
            if not pageset.intersection(umapset):
                continue

            db.newPage(args.pagesize)
            db.font(BLOCK_TITLE_FONT, BLOCK_TITLE_SIZE)
            db.textBox(f'{blockname} (U+{blockpagemin:04X}-{blockpagemax:04X})',
                       (0, db.height() - 60, db.width(), 36),
                       align="center")
            if _bpi == 0:
                db.linkDestination(blockname, (0, db.height()))

            db.font(CHART_LABEL_FONT, BLOCK_FONTNAME_SIZE)
            db.textBox(f'{fontname}',
                       (0, db.height() - BLOCK_FONTNAME_Y_OFFSET, db.width(), 20),
                       align="center")
            db.linkRect("index0",
                        (0, db.height() - BLOCK_FONTNAME_Y_OFFSET, db.width(), 18))

            npagecols = min(ceil((block_nmax - blockpagemin) / 16), 16)
            chart_width = npagecols * CHART_COL_WIDTH
            chart_left = (db.width() / 2) - (chart_width / 2)
            db.stroke(0)

            CHART_BOX_TOP = db.height() - 80
            CHART_BOX_BOT = CHART_BOX_TOP - (CHART_ROW_HEIGHT * 16)
            xpos = 0

            for col in range(npagecols):
                db.lineCap("square")
                db.strokeWidth(THICK if col == 0 else THIN)
                xpos = chart_left + col * CHART_COL_WIDTH
                db.line((xpos, CHART_BOX_TOP), (xpos, CHART_BOX_BOT))
                colheader = (blockpagemin + (16 * col)) // 16
                db.strokeWidth(0)
                db.font(CHART_LABEL_FONT, CHART_LABEL_SIZE)
                # top column label
                ypos = CHART_BOX_TOP
                db.textBox(f'{colheader:03X}',
                           (xpos, ypos + CHART_COL_LABEL_Y_OFFSET, CHART_COL_WIDTH, 16),
                           align="center")

                # the actual font characters
                db.strokeWidth(THICK)
                db.line((chart_left + 1, ypos),
                        (chart_left + chart_width, ypos))
                ypos -= CHART_ROW_HEIGHT
                db.font(CHART_LABEL_FONT, CHART_LABEL_SIZE)
                set_vf()
                for uc in range(colheader * 16, (colheader * 16) + 16):
                    if uc // 16 == colheader:
                        db.strokeWidth(THICK if uc % 16 == 15 else THIN)
                        db.line((chart_left, ypos), (chart_left + chart_width - 1, ypos))
                        db.strokeWidth(0)
                        db.font(CHART_LABEL_FONT, CHART_LABEL_SIZE)
                        # left-side row label
                        db.textBox(f'{uc % 16:X}',
                                   (chart_left - 12, ypos + CHART_ROW_LABEL_Y_OFFSET, 8, 20),
                                   align="right")
                    if uc in umap:
                        # code label
                        db.strokeWidth(0)
                        db.font(CODE_LABEL_FONT, CODE_LABEL_SIZE)
                        db.textBox(f'{uc:04X}',
                                   (xpos, ypos - CODE_LABEL_Y_OFFSET, CHART_COL_WIDTH - 2, 20),
                                   align="center")
                    ypos -= CHART_ROW_HEIGHT

                # draw font glyphs all in one go
                ypos = CHART_BOX_TOP - CHART_ROW_HEIGHT
                db.strokeWidth(0)
                db.font(font_file, CHART_FONT_SIZE)
                for uc in range(colheader * 16, (colheader * 16) + 16):
                    ucc = chr(uc)
                    gc = unicodedataplus.category(ucc)

                    if gc == "Cn":
                        # for Unassigned characters (gc=Cn), fill gray
                        with db.savedState():
                            db.fill(0, alpha=.25)
                            db.rect(xpos, ypos, CHART_COL_WIDTH, CHART_ROW_HEIGHT)

                    if uc in umap:
                        bl = ypos + CHART_FONT_BL + tbfbo
                        txt = db.FormattedString(
                            chr(uc),
                            font=font_file,
                            fontSize=args.size,
                            align="center",
                            fontVariations=set_vf())
                        sc = unicodedataplus.script(chr(uc))
                        if gc == "Mn" and sc == "Inherited":
                            txt = NSMARKBASE + txt  # dotted circle base
                        db.textBox(txt,
                                   (xpos, bl, CHART_COL_WIDTH, CHART_ROW_HEIGHT),
                                   align="center")
                    ypos -= CHART_ROW_HEIGHT

            # right line
            db.strokeWidth(THICK if blockpagemax // 16 == block_nmax // 16 else THIN)
            db.line((xpos + CHART_COL_WIDTH, CHART_BOX_TOP),
                    (xpos + CHART_COL_WIDTH, CHART_BOX_BOT))


def save_document(output_path):
    db.saveImage(output_path)
    print('saved PDF to', output_path)
    subprocess.call(['open', output_path])
    db.endDrawing()


if __name__ == '__main__':
    if IN_UI:
        file_or_folder = getFileOrFolder(allowsMultipleSelection=False)
        input_dir = str(file_or_folder[0])
        args = get_options([input_dir])

    else:
        args = get_options()

    font_paths = get_font_paths(args.input_dir)
    sorted_font_paths = sort_fonts(font_paths)

    for font_path in sorted_font_paths:
        make_chart_doc(font_path, args)

        if not IN_UI:
            out_name = args.output_file_name or font_path.parent / f'{font_path.stem}_chart.pdf'
            save_document(out_name)
