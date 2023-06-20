# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Create the README.md for this repository.

    python makeReadme.py > README.md

For this process to work, scripts must have the
`if __name__ == '__main__':` statement in them,
which is typical for modules.

'''

import ast
import os
import importlib

header = '''\
# DrawBot-based font- and UFO proofing scripts

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

'''

footer = '''
## Acknowledgements

- "en_10k.txt" is based on [en_50k.txt](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/content/2016/en/en_50k.txt) from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords) project, Copyright (c) 2016 Hermit Dave
- fonts included in this distribution are subject to the SIL Open Font License, Copyright 2016-2023 Adobe.
'''

ignore = ['__init__.py']

if __name__ == '__main__':

    print(header)

    for file_name in sorted(os.listdir('.')):
        if file_name not in ignore:
            base_name, suffix = os.path.splitext(file_name)
            if suffix == '.py':
                try:
                    module = importlib.import_module(base_name)
                    docstring = module.__doc__

                except ModuleNotFoundError:
                    body = ast.parse(''.join(open(file_name)))
                    docstring = '\n' + ast.get_docstring(body) + '\n'

                if docstring:
                    print(f'### `{file_name}`')
                    print(docstring)
                    print('----')
                    print()

    print(footer)
