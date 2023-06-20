# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

import time


def timestamp(readable=False, connector=' '):
    '''
    return a time stamp -- numbers are either separated by dashes (great for
    file names) or with slashes and colons (human-readable).

    The connector argument is the character which connects date and time.
    '''
    local_time = time.localtime()

    if readable:
        conn_date = '/'
        conn_time = ':'
    else:
        conn_date = '-'
        conn_time = ''
    stamp_date = time.strftime(f'%Y{conn_date}%m{conn_date}%d', local_time)
    stamp_time = time.strftime(f'%H{conn_time}%M{conn_time}%S', local_time)

    return f'{stamp_date}{connector}{stamp_time}'
