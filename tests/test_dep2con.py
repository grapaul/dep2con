"""Integration tests for the public dep2con API."""

from pathlib import Path

from dep2con import Dep2Con, make_const


CONLLU_FIXTURE = """# sent_id = 1
# text = Cats sleep.
# source = test
1	Cats	cat	NOUN	_	Number=Plur	2	nsubj	_	_
2	sleep	sleep	VERB	_	_	0	root	_	_
3	.	.	PUNCT	_	_	2	punct	_	_
"""


def test_make_const_returns_named_sentence_results(tmp_path: Path) -> None:
    """A CoNLL-U input produces an object with the documented attributes."""
    input_file = tmp_path / "input.conllu"
    input_file.write_text(CONLLU_FIXTURE, encoding="utf-8")

    results = make_const(str(input_file))

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, Dep2Con)
    assert result.sent_parse
    assert result.sent_text == " Cats sleep."
    assert result.sent_len == 2
    assert result.sentence_index == "Cats sleep."
    assert result.source == "test"
