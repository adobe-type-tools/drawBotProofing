# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Creates pages of example words for a list of fonts, arranged in waterfall-like
fashion (both vertically and horizontally).

The proof text comes from the waterfall_horizontal and waterfall_vertical text
files found in the `_content` folder.

Input:
* folder containing font files

'''

import argparse
import subprocess
import drawBot as db
from pathlib import Path

from .proofing_helpers import fontSorter
from .proofing_helpers.files import get_font_paths, read_text_file
from .proofing_helpers.formatter import RawDescriptionAndDefaultsFormatter
from .proofing_helpers.names import get_family_name, get_name_overlap


def get_args():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionAndDefaultsFormatter)

    parser.add_argument(
        'input',
        action='store',
        metavar='INPUT',
        nargs='+',
        help='font file(s) or folder(s)')

    parser.add_argument(
        '--pointsize', '-p',
        action='store',
        default=40,
        type=int,
        help='point size')

    parser.add_argument(
        '-k', '--kerning_off',
        default=False,
        action='store_true',
        help='switch off kerning')

    parser.add_argument(
        '--onum',
        default=False,
        action='store_true',
        help='old-style figures')

    parser.add_argument(
        '--pnum',
        default=False,
        action='store_true',
        help='proportional figures')

    return parser.parse_args()


def make_output_name(fonts):
    '''
    Make a sensible filename for the PDF proof created.

    '''
    chunks = ['waterfall proof']
    all_family_names = sorted(set([get_family_name(font) for font in fonts]))

    family_name_overlap = get_name_overlap(all_family_names)

    if family_name_overlap:
        chunks.append(family_name_overlap)
    else:
        if len(all_family_names) == 1:
            chunks.append(all_family_names[0])
        elif len(all_family_names) == 2:
            chunks.append(', '.join(all_family_names))
        else:
            chunks.append(', '.join(all_family_names[:2]) + ' etc')

    pdf_name = ' '.join(chunks) + '.pdf'
    return pdf_name


def make_proof(fonts, args):
    content_dir = Path(__file__).parent / '_content'
    v_content = read_text_file(content_dir / 'waterfall_vertical.txt')
    h_content = read_text_file(content_dir / 'waterfall_horizontal.txt')

    db.newDrawing()
    pt_size = args.pointsize
    leading = pt_size * 1.2
    margin = 48

    # create a new page for each word in the vertical content text file:
    for line in v_content.split('\n'):

        feature_dict = {
            'kern': not args.kerning_off,
            'onum': args.onum,
            'pnum': args.pnum,
        }

        db.newPage('Legal')
        top_line = db.height() - pt_size - margin
        offset = top_line
        for f_index, font in enumerate(fonts):
            offset = top_line - f_index * leading
            fs = db.FormattedString(
                line,
                font=font,
                fontSize=pt_size,
                openTypeFeatures=feature_dict,
            )
            db.text(fs, (margin, offset))

    # Create a page with horizontal waterfall content:
    db.newPage('LegalLandscape')
    top_line = db.height() - pt_size - margin

    for word_index, word in enumerate(h_content.split('\n')):
        offset = top_line - word_index * leading

        fs = db.FormattedString(fontSize=pt_size)
        for font in fonts:
            fs.append(word, font=font)

        db.text(fs, (margin, offset))

    output_name = make_output_name(fonts)
    output_path = Path(f'~/Desktop/{output_name}').expanduser()
    db.saveImage(output_path)
    db.endDrawing()
    print(f'saved to {output_path}')
    subprocess.call(['open', output_path])


def collect_fonts(inputs):

    fonts = []
    input_paths = [Path(i) for i in inputs]
    if all([p.exists() for p in input_paths]):
        if all([ip.is_file() for ip in input_paths]):
            # all font files. no sorting
            for ip in input_paths:
                fonts.extend(get_font_paths(ip))
        else:
            # at least some folders. sort per folder
            for ip in input_paths:
                sorted_fonts = fontSorter.sort_fonts(
                    get_font_paths(ip), alternate_italics=True)
                fonts.extend(sorted_fonts)

    return fonts


def main():
    args = get_args()
    fonts = collect_fonts(args.input)
    if fonts:
        make_proof(fonts, args)
    else:
        print(f'could not find any fonts')


if __name__ == '__main__':
    main()
