# Copyright 2023 Adobe
# All Rights Reserved.

# NOTICE: Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying
# it.

'''
Create/update the README.md file for this repository.

    python3 makeReadme.py

'''

import ast
from pathlib import Path


def make_doc_snippet(file):
    '''
    Read the doc string of a Python script, and return it in markdown format.
    If an image file (corresponding to the script name) exists in an _images
    folder, add a reference to that image.
    '''
    doc_snippet = None

    # very simple way of looking for related images
    images = sorted([
        img for img in Path('_images/').iterdir() if
        img.name.startswith(file.stem) and
        img.suffix == '.png'])

    if file.suffix == '.py' and file.name != '__init__.py':
        body = ast.parse(''.join(open(file)))
        docstring = ast.get_docstring(body)

        if docstring:
            doc_snippet = f'### `{file.name}`\n\n{docstring}\n'
            if images:
                for image_file in images:
                    doc_snippet += f'\n![{file.name}](_images/{image_file.name})\n'
            doc_snippet += '\n----\n'

    return doc_snippet


header = '''\
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

'''

footer = '''
## Acknowledgements

- "en_10k.txt" is based on [en_50k.txt](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/content/2016/en/en_50k.txt) from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords) project, Copyright (c) 2016 Hermit Dave
- fonts included in this distribution are subject to the SIL Open Font License, Copyright 2016-2023 Adobe.
- Unicode and the Unicode Logo are registered trademarks of Unicode, Inc. in the United States and other countries.

'''


if __name__ == '__main__':

    output = []
    output.append(header)

    for file in sorted(Path('drawbot_proofing').iterdir()):
        doc_snippet = make_doc_snippet(file)
        if doc_snippet:
            output.append(doc_snippet)

    output.append(footer)

    with open('README.md', 'w') as readme_blob:
        readme_blob.write('\n'.join(output))
