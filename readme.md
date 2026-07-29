# dep2con

`dep2con` converts Universal Dependencies (UD) parses into constituency
representations. It accepts either a CoNLL-U format or text for the
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

## Usage

```python
from dep2con import make_const
```

#### Simple usage (for string parsing):

```bash
t_s = make_const("I saw a UFO in the backyard.", lang = 'en', use_parser = True)

for dep2con in t_s:
    print(dep2con.sent_parse)
    for i in dep2con.x_phrases:
        print(i)
```
`[VP [NP I] saw [NP a UFO] [PP in [NP the backyard]]] .`  
`...`  
`  NPs:`  
`I`  
`a UFO`  
`the backyard`  
`  VPs:`  
`I saw a UFO in the backyard`  
`  PPs:`  
`in the backyard`  

#### More on usage (for a CoNLL-U format):

```
t_s = make_const("conllu")

for dep2con in t_s:
    print(dep2con.sent_parse)
    print(dep2con.x_phrases)
    print(dep2con.sentence_index)
    ...
```

#### Output attributes:

`make_const()` returns a list with one `Dep2Con` object per input sentence.
Each result has these attributes:

- `sent_parse` - a constituency tree for the sentence
- `x_phrases` - constituents for the specified phrases
- `sent_dict` - a dictionary format for a sentence UD `{1: {'idw': 1, 'wf': 'I', 'nf': 'I', 'pos': 'PRON', 'xpos': '_', 'tags': 'Case=Nom|Number=Sing|Person=1|PronType=Prs', 'head_id': 2, 'rel': 'nsubj', 'deps': '_', 'misc': '_'},...`
- `sent_text` - sentence text
- `sent_len` - sentence length
- `sentence_index` - an index of a sentence in a text 
- `source` - sentence source if mentioned in a CoNLL-U file

#### Input arguments:

- `input`: str, **obligatory**. Is string if `use_parser = True`, otherwise input in conllu format
- `lang`: str, the language parameter ('en',...) in case of text parsing
- `use_parser`: bool, True - the Stanza parser is at work; False - input in the conllu format, `default = False`
- `delete_orth`: bool, delete orthography from the final tree, `default = False`
- `xps`: bool, return specific phrases separately, `default = True`
- `emb`: bool, returns subconstituents, not only maximal projection, if True, `default = True`
- `h_terminals`: List[str], terminals to be put in brackets w/out dependents, `default = ['NOUN', 'PRON', 'PROPN', 'ADV']`
- `selected_cons`: List[str],  when we want some specific constituents only, `default = ['NP', 'VP', 'PP', 'AP', 'AdvP', 'NumP', 'PartP', 'CCONJP', 'INTJP', 'Particle', 'SCONJP', 'SYMP', 'XP']`

