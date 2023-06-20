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


### `makeReadme.py`

Create/update the README.md file for this repository.

    python makeReadme.py > README.md

----


## Acknowledgements

- "en_10k.txt" is based on [en_50k.txt](https://github.com/hermitdave/FrequencyWords/blob/525f9b560de45753a5ea01069454e72e9aa541c6/content/2016/en/en_50k.txt) from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords) project, Copyright (c) 2016 Hermit Dave
- fonts included in this distribution are subject to the SIL Open Font License, Copyright 2016-2023 Adobe.

