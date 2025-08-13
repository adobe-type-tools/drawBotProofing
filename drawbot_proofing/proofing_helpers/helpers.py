# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import unicodedata


def uni_names(characters):
    output = []
    for char in sorted(characters):
        try:
            uni_name = unicodedata.name(char)
        except ValueError:
            uni_name = 'XXXX'
        output.append(f'{char} U+{ord(char):04X} {uni_name}')
    return output
