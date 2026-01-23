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


def is_rtl(text):
    '''
    check if a given text is RTL or LTR
    https://www.unicode.org/reports/tr44/tr44-34.html#Bidi_Class_Values
    '''

    bidi_analysis = [unicodedata.bidirectional(char) for char in text]
    rtl_count = bidi_analysis.count('R') + bidi_analysis.count('AL')
    ltr_count = bidi_analysis.count('L')

    if rtl_count > ltr_count:
        return True
    else:
        return False
