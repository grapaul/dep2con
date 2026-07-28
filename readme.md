# dep2con

`dep2con` converts Universal Dependencies (UD) parses into constituency
representations. It accepts either a CoNLL-U file or text processed with the
Stanza dependency parser.

## Requirements

- Python 3.14 or newer
- `pyconll` 4.0 or newer for CoNLL-U input
- `stanza` when parsing raw text

## Installation

Install the published package:

```bash
python -m pip install dep2con
```

For development from a clone:

```bash
python -m pip install -e ".[dev]"
```

## Usage

```python
from dep2con import make_const

results = make_const("input.conllu")

for dep2con in results:
    print(dep2con.sent_parse)
    print(dep2con.sent_text)
    print(dep2con.x_phrases)
```

`make_const()` returns a list with one `Dep2Con` object per input sentence.
Each result has these attributes:

- `sent_parse`
- `x_phrases`
- `sent_dict`
- `sent_text`
- `sent_len`
- `sentence_index`
- `source`

To parse raw text instead of loading CoNLL-U:

```python
results = make_const("Cats sleep.", lang="en", use_parser=True)
```

## Development

Run the test suite:

```bash
python -m pytest
```

Build distributable files:

```bash
python -m build
```
