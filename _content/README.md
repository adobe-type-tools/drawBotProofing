# Text files for proofing

These text files contain sentences which correspond to a given Adobe character set. The text files are cumulative, which means (for example) the AL-3 file will only contain examples which make that set different from AL-2, and not contain any sentences which could be composed using AL-2 characters only. AL-1 contains paragraphs with characters that make AL-1 different from ASCII.

The text files are used for various proofing scripts (e.g. `textProof.py`), and are all strung together using the `chain_charset_texts` method within the `proofing_helpers.files` module.


## Status of proofing files

### Latin

- ASCII.txt: complete coverage

- AL1.txt: complete coverage

- AL2.txt: complete coverage

- AL3.txt: complete coverage

- AL4.txt: examples missing for ~60 characters

- AL5.txt: examples missing for over 600 characters

### Cyrillic

- AC1.txt: complete coverage

- AC2.txt: complete coverage

- AC3.txt: examples missing for ~20 characters

### Greek

- AG1.txt: examples missing for 3 characters

- AG2.txt: examples missing for ~150 characters


## Updating text files

The script `text_groom.py` was written for that purpose.

- run it to re-sort and re-categorize all text files.
- find a favorite character to add
- sift through Wikipedia or another source of copyright-free text to find a good, as-natural-as-possible sentence
- add the sentence to one of the text files (within a writing system, it does not make a difference which text file the sentence is added to)
- re-run `text_groom.py` and repeat.

NB: An effort was made to find copyright-free in-use examples for as many characters as possible (Wikipedia). However, this is not always feasible, especially for rare code points.
