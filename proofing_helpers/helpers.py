# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import unicodedata


def list_uni_names(characters):
    for char in sorted(characters):
        try:
            uni_name = unicodedata.name(char)
        except ValueError:
            uni_name = 'XXXX'
        print(f'\t{char} U+{ord(char):04X} {uni_name}')
