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


def get_short_name(file):
    with open('pyproject.toml') as blob:
        toml_lines = blob.read().splitlines()

    commands = [li for li in toml_lines if li.endswith(':main"')]
    for line in commands:
        short_name, module_name = line.split(' = ')
        if module_name == f'"drawbot_proofing.{file.stem}:main"':
            return short_name


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
        headline = get_short_name(file)
        if not headline:
            headline = file.name
        body = ast.parse(''.join(open(file)))
        docstring = ast.get_docstring(body)

        if docstring:
            doc_snippet = f'### `{headline}`\n\n{docstring}\n'
            if images:
                for image_file in images:
                    doc_snippet += f'\n![{file.name}](_images/{image_file.name})\n'
            doc_snippet += '\n----\n'

    return doc_snippet


header = '''\
# DrawBot scripts for proofing fonts and/or UFOs.

## Prerequisites

- we recommend using a Python virtual environment. You can easily create
and activate one with the following commands in Terminal:

```bash
python3 -m venv my_venv
source my_venv/bin/activate
```

- once you have a virtual environment activated, the proofing tools themselves
can be installed via `pip`:

```bash
pip install git+https://github.com/adobe-type-tools/drawBotProofing.git
```
Further installation instructions can be found in [INSTALLATION.md](INSTALLATION.md).

You’re now ready to start proofing!

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
