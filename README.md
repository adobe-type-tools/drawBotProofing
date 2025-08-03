# DrawBot scripts for proofing fonts and/or UFOs.

## Prerequisites

- we recommend using a Python virtual environment. You can easily create and activate one with the
following commands in Terminal:
```
python3 -m venv my_venv
source my_venv/bin/activate
```

- once you have a virtual environment activated, install `drawBot` and script dependencies by running
the following command from the same directory where this file resides:
```
python -m pip install -r requirements.txt
```

You're now ready to run the scripts!

----


### `accentProof.py`

Proof of all accents with a representation of all glyphs using that accent,
and example words for each accent (both upper- and lowercase).
Additionally, words with “merged” non-abc glyphs (such as æðøß) will be shown.

This script is currently limited to AL-3, an extension to AL-4 and beyond is
thinkable.

Input: single font or folder containing font files.

![accentProof.py](_images/accentProof.png)

----

### `alphabetProof.py`

Creates example pages for:

- general alphabet (upper- and lowercase)
- spacing proofs
- some sample words

Modes (`proof`, `spacing`, `sample`) can be chosen individually, or all at once
(`all`). Writing systems supported are `lat`, `grk`, `cyr`, and `figures`.

Input: one or more font files.

![alphabetProof.py](_images/alphabetProof_1.png)

![alphabetProof.py](_images/alphabetProof_2.png)

![alphabetProof.py](_images/alphabetProof_3.png)

----

### `charsetProof.py`

Visualizes a given (Adobe) character set.
The default charset is AL-3. Code points not supported in the font at hand will
be shown as a .notdef glyph (but are still present as text in the PDF file).

More information on Adobe’s character sets:

- [Latin](https://github.com/adobe-type-tools/adobe-latin-charsets)
- [Cyrillic](https://github.com/adobe-type-tools/adobe-cyrillic-charsets)
- [Greek](https://github.com/adobe-type-tools/adobe-greek-charsets)

Input: font file(s) or folder of fonts.

![charsetProof.py](_images/charsetProof_1.png)

![charsetProof.py](_images/charsetProof_2.png)

![charsetProof.py](_images/charsetProof_3.png)

----

### `comparisonProof.py`

Create lines for a string of characters, set in all fonts that support it.
The choice of fonts is either all installed fonts (no argument), or all fonts
in a given folder tree. The font list can be filtered by supplying a regular
expression.

This proof helps solving the question:
“How do other fonts deal with this weird glyph?”

Slow.

![comparisonProof.py](_images/comparisonProof_1.png)

![comparisonProof.py](_images/comparisonProof_2.png)

![comparisonProof.py](_images/comparisonProof_3.png)

----

### `contextProof.py`

Creates example pages for usage of a specific letter or letter combination.

Needs a word list as an input file, such as the word lists available at
https://github.com/hermitdave/FrequencyWords/tree/master/content/2016

Input: font file(s) or folder of fonts.

![contextProof.py](_images/contextProof_1.png)

![contextProof.py](_images/contextProof_2.png)

----

### `figureSpacingProof.py`

Simple script check figure spacing in UFOs (without kerning).
For each figure suffix (such as .tosf), a new spacing page is made.

Input: folder containing UFO or font files, or individual font- or UFO files.

![figureSpacingProof.py](_images/figureSpacingProof.png)

----

### `glyphProof.py`

Creates a PDF document which helps comparing glyphs to each other.
Various modes are possible – the default is an
[Autopsy](https://vimeo.com/116063612)-like showing of glyphs in a grid view.
Other modes include `gradient` (horizontal waterfall), `single` (page-by-page),
and `overlay` (superimposed outline view).

Input: folder containing UFO files or fonts, or individual UFOs/fonts.
In the input filtering process, UFO files are preferred to fonts.

![glyphProof.py](_images/glyphProof_1.png)

![glyphProof.py](_images/glyphProof_2.png)

![glyphProof.py](_images/glyphProof_3.png)

![glyphProof.py](_images/glyphProof_4.png)

----

### `glyphsetProof.py`

Visualizes the complete glyphset of a font or UFO on a single page.
The output is good to use with a diffing tool like `diff-pdf` in a later step.

The glyphset can be filtered with a regular expression (for example,
use `-r ".*dieresis"` to show all glyphs whose names end with -dieresis).

Input: folder containing UFO or font files, or individual font- or UFO files.

![glyphsetProof.py](_images/glyphsetProof_1.png)

![glyphsetProof.py](_images/glyphsetProof_2.png)

![glyphsetProof.py](_images/glyphsetProof_3.png)

----

### `textProof.py`

Create example paragraphs corresponding to a given character set.

Default mode is creating single-page PDF with a random subset of the requested
charset. Optionally, a full charset can be consumed systematically, to show
as many characters as possible.
The alternative mode is using a text file as input, to achieve more predictable
(and comparable) output. In text-mode, the output still is limited to a single
page (no matter how long the text file may be).

Known bug:
Line spacing may become inconsistent if a character set beyond the font’s
character support is requested (this is a macOS limitation caused by the
vertical metrics in a given fallback font).

Input:
* choice of text file or charset name
* single font file, or folder containing fonts
* optional secondary font(s) (for mixing Roman/Italic, for example)

![textProof.py](_images/textProof_1.png)

![textProof.py](_images/textProof_2.png)

![textProof.py](_images/textProof_3.png)

----

### `unicodeChartProof.py`

Creates character charts similar to those appearing in The Unicode® Standard,
but using the supplied font (and only the characters present in the font).

Input: font file or folder containing font files

CLI Inputs: see help

![unicodeChartProof.py](_images/unicodeChartProof_1.png)

![unicodeChartProof.py](_images/unicodeChartProof_2.png)

![unicodeChartProof.py](_images/unicodeChartProof_3.png)

----

### `verticalMetricsComparisonProof.py`

Creates pages with example characters to visualize the variation
of vertical metrics across a typeface family.

Input: folder containing font or UFO files.

![verticalMetricsComparisonProof.py](_images/verticalMetricsComparisonProof.png)

----

### `verticalMetricsProof.py`

Creates simple view which illustrates all vertical metrics
set in the font metadata. Additionally, tallest and lowest glyphs are shown.

Using the -n option, the number of extreme glyphs can be increased.

Input: font file

![verticalMetricsProof.py](_images/verticalMetricsProof_1.png)

![verticalMetricsProof.py](_images/verticalMetricsProof_2.png)

![verticalMetricsProof.py](_images/verticalMetricsProof_3.png)

----

### `waterfallProof.py`

Creates pages of example words for a list of fonts, arranged in waterfall-like
fashion (both vertically and horizontally).

The proof text comes from the waterfall_horizontal and waterfall_vertical text
files found in the _content folder.

Input: folder containing font files.

![waterfallProof.py](_images/waterfallProof_1.png)

![waterfallProof.py](_images/waterfallProof_2.png)

----


## Acknowledgements

- "en_10k.txt" is based on [en_50k.txt](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/content/2016/en/en_50k.txt) from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords) project, Copyright (c) 2016 Hermit Dave
- fonts included in this distribution are subject to the SIL Open Font License, Copyright 2016-2023 Adobe.
- Unicode and the Unicode Logo are registered trademarks of Unicode, Inc. in the United States and other countries.

