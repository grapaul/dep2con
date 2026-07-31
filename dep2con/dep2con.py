"""Convert dependency-based sentence representations to constituency output."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Tuple


WordData = Dict[str, Any]
SentenceData = Dict[int, WordData]
ConstituencyMap = Dict[int, List[int]]
BracketMap = Dict[int, List[int]]


@dataclass
class Dep2Con:
    """Constituency-conversion result for one input sentence."""

    sent_parse: str
    x_phrases: Any
    sent_dict: SentenceData
    sent_text: str
    sent_len: int
    sentence_index: Any
    source: str


def len_text(sent_dict: Mapping[int, WordData]) -> Tuple[str, int]:
    """Return sentence text and the number of non-punctuation tokens."""
    text_parts: List[str] = []
    non_punctuation_count = 0

    for word in sent_dict.values():
        if word['pos'] == 'PUNCT':
            text_parts.append(word['wf'])
        else:
            non_punctuation_count += 1
            text_parts.extend((' ', word['wf']))

    return ''.join(text_parts), non_punctuation_count


def wf_to_dic(wf_string: str) -> WordData:
    """Convert one tab-separated UD token line into the internal word mapping."""
    word_data: WordData = {}
    fields = wf_string[:-1].split('\t')
    if (
            len(fields) < 7
            or wf_string.startswith('#')
            or not fields[0].isdigit()
    ):
        return {}

    part_of_speech = 'PTCPL' if 'VerbForm=Part' in fields[4] else fields[3]
    word_data = {
        'idw': int(fields[0]),
        'wf': fields[1],
        'nf': fields[2],
        'pos': part_of_speech,
        'xpos': '_',
        'tags': fields[4],
        'head_id': 0 if fields[5] == 'root' else int(fields[5]),
        'rel': fields[6],
        'deps': '_',
        'misc': '_',
    }

    return word_data


def stanza_to_ud(ind: Any, sent: Any, use_parser: bool) -> List[str]:
    """Convert a Stanza or PyConll sentence to the module's UD-line format."""
    text = sent.meta.get("text") or '' if not use_parser else sent.text
    lines = ['\n# ', str(ind), ' ', text, '\n']
    tokens = sent.words if use_parser else sent.tokens

    for token in tokens:
        word_form = token.text if use_parser else token.form
        part_of_speech = token.pos if use_parser else token.upos
        fields = (
            token.id,
            word_form,
            token.lemma,
            part_of_speech,
            token.feats,
            token.head,
            token.deprel,
        )
        lines.extend(
            f'{field}\t' if field != 'NoneType' else '-\t'
            for field in fields
        )
        lines.append('\n')

    return ''.join(lines).split('\n')


def sent_dict_from_sents(ind: Any, sent: Any, use_parser: bool) -> SentenceData:
    """Build an ID-indexed internal representation for a sentence."""
    sentence_words: SentenceData = {}

    for word_line in stanza_to_ud(ind, sent, use_parser):
        word_data = wf_to_dic(word_line)
        if len(word_line) > 1 and word_data:
            sentence_words[word_data['idw']] = word_data

    return sentence_words


def check_head(
    const: ConstituencyMap, sent_w_dicts: Mapping[int, WordData]
) -> Tuple[bool, str]:
    """Validate dependency heads and detect cyclic dependencies."""
    correct = True
    error_type = ''

    for head_id in const:
        head_list = set(const[head_id])
        new_children = const[head_id]
        while new_children and head_id not in head_list:
            child_heads = [child for child in new_children if child in const]
            new_children = []
            for child_head in child_heads:
                head_list.update(const[child_head])
                new_children = const[child_head]
        if head_id in head_list:
            correct, error_type = False, 'Cyclic heads '
            break

    for word in sent_w_dicts.values():
        if word['head_id'] == 0 and word['rel'] != 'root':
            correct, error_type = False, 'Root with wrong relation '

    return correct, error_type


def heads(sent_in_dics: Iterable[WordData]) -> List[int]:
    """Return sorted IDs of words that have dependents."""
    return sorted({word['head_id'] for word in sent_in_dics if word['head_id'] != 0})


def rearrange_pp(sent_in_dics: SentenceData) -> SentenceData:
    """Promote adpositions in the internal dependency representation."""
    for word in sent_in_dics.values():
        if word['pos'] == 'ADP' and word['rel'] != 'root':
            head_id = sent_in_dics[word['head_id']]['idw']
            adposition_id = word['idw']
            grandparent_id = sent_in_dics[head_id]['head_id']
            sent_in_dics[adposition_id]['head_id'] = grandparent_id
            sent_in_dics[head_id]['head_id'] = adposition_id

            adposition_relation = sent_in_dics[adposition_id]['rel']
            head_relation = sent_in_dics[head_id]['rel']
            sent_in_dics[adposition_id]['rel'] = head_relation
            sent_in_dics[head_id]['rel'] = adposition_relation

    return sent_in_dics


def rearrange_cop(sent_in_dics: SentenceData) -> SentenceData:
    """Promote eligible copulas and reattach selected dependents."""
    copula: WordData = {}
    nominal_predicate: WordData = {}

    for word in sent_in_dics.values():
        if (
            word['pos'] == 'AUX'
            and word['head_id'] != 0
            and sent_in_dics[word['head_id']]['pos'] not in ['VERB', 'ADP']
        ):
            nominal_predicate, copula = sent_in_dics[word['head_id']], word
            if nominal_predicate['head_id'] == 0:
                nominal_predicate['head_id'], nominal_predicate['rel'] = (
                    word['idw'],
                    'cop',
                )
                word['head_id'], word['rel'] = 0, 'root'
            if (
                nominal_predicate['head_id'] != 0
                and sent_in_dics[nominal_predicate['head_id']]['head_id'] == 0
            ):
                parent = sent_in_dics[nominal_predicate['head_id']]
                parent['head_id'], parent['rel'] = word['idw'], 'cop'
                word['head_id'], word['rel'] = 0, 'root'

    for dependent in sent_in_dics.values():
        if (
            copula
            and nominal_predicate
            and dependent['head_id'] == nominal_predicate['idw']
            and dependent['rel'] in ['nsubj', 'advmod', 'obl']
        ):
            dependent['head_id'] = copula['idw']

    return sent_in_dics


def find_children(
    head_ids: Iterable[int], sent_in_dics: Mapping[int, WordData]
) -> Tuple[ConstituencyMap, Dict[str, List[str]]]:
    """Return dependent IDs and forms grouped by each head ID."""
    constituents: ConstituencyMap = {}
    constituent_words: Dict[str, List[str]] = {}

    for head_id in head_ids:
        children: List[int] = []
        child_words: List[str] = []
        for word in sent_in_dics.values():
            if word['head_id'] == head_id:
                children.append(word['idw'])
                child_words.append(word['wf'])
        constituents[head_id] = children
        constituent_words[sent_in_dics[head_id]['wf']] = child_words

    return constituents, constituent_words


def find_brackets_l(
    sent_w_dicts: Mapping[int, WordData],
    const: Mapping[int, List[int]],
    h_terminals: List[str],
) -> BracketMap:
    """Find left brackets for constituency spans."""
    left_brackets: BracketMap = {int(word['idw']): [] for word in sent_w_dicts.values()}

    for head_id, children in const.items():
        bracket_path, current_id = [head_id], head_id
        if children[0] < head_id and children[0] in const:
            while const[current_id][0] in const:
                current_id = const[current_id][0]
                bracket_path.append(
                    (
                        const[current_id][0]
                        if const[current_id][0] < current_id
                        else current_id
                    )
                )
            left_brackets[min(bracket_path)].append(head_id)
        elif children[0] < head_id:
            left_brackets[children[0]].append(head_id)
        elif children[0] > head_id:
            left_brackets[head_id].append(head_id)

    for word_id, bracket_ids in left_brackets.items():
        if sent_w_dicts[word_id]['pos'] in h_terminals and word_id not in const:
            bracket_ids.append(sent_w_dicts[word_id]['idw'])

    return left_brackets


def find_brackets_r(
    sent_w_dicts: Mapping[int, WordData],
    const: Mapping[int, List[int]],
    h_terminals: List[str],
) -> BracketMap:
    """Find right brackets for constituency spans."""
    right_brackets: BracketMap = {
        int(word['idw']): [] for word in sent_w_dicts.values()
    }

    for head_id, children in const.items():
        bracket_path, current_id = [head_id], head_id
        if children[-1] > head_id and children[-1] in const:
            while const[current_id][-1] in const:
                current_id = const[current_id][-1]
                bracket_path.append(
                    (
                        const[current_id][-1]
                        if const[current_id][-1] > current_id
                        else current_id
                    )
                )
            right_brackets[max(bracket_path)].append(head_id)
        elif children[-1] > head_id:
            right_brackets[children[-1]].append(head_id)
        elif children[-1] < head_id:
            right_brackets[head_id].append(head_id)

    for word_id, bracket_ids in right_brackets.items():
        if sent_w_dicts[word_id]['pos'] in h_terminals and word_id not in const:
            bracket_ids.append(sent_w_dicts[word_id]['idw'])

    return right_brackets


def post_proc(
    brackets: BracketMap, sent_w_dicts: Mapping[int, WordData], t: int
) -> BracketMap:
    """Move brackets around punctuation, sort them, and remove empty entries."""
    if t == 0:
        for word_id, bracket_ids in brackets.items():
            if sent_w_dicts[word_id]['rel'] == 'punct':
                if word_id + 1 in brackets:
                    brackets[word_id + 1].extend(bracket_ids)
                brackets[word_id] = []
        for bracket_ids in brackets.values():
            bracket_ids.sort(reverse=True)

    if t == 1:
        for word_id, bracket_ids in brackets.items():
            if sent_w_dicts[word_id]['rel'] == 'punct':
                preceding_ids = [
                    candidate_id
                    for candidate_id in brackets
                    if candidate_id < word_id
                ]
                if preceding_ids:
                    preceding_id = max(preceding_ids)
                    brackets[preceding_id].extend(bracket_ids)
                    brackets[word_id] = []

        for bracket_ids in brackets.values():
            bracket_ids.sort()

    return {word_id: ids for word_id, ids in brackets.items() if ids}


PHRASE_DICT = {
    'NOUN': 'NP', 'PRON': 'NP', 'PROPN': 'NP', 'DET': 'NP', 'ADJ': 'AP',
    'ADP': 'PP', 'ADV': 'AdvP', 'VERB': 'VP', 'AUX': 'VP',
    'CCONJ': 'CCONJP', 'INTJ': 'INTJP', 'NUM': 'NumP', 'PART': 'Particle',
    'PUNCT': 'PUNCTP', 'SCONJ': 'SCONJP', 'SYM': 'SYMP', 'X': 'XP',
    'PTCPL': 'PartP',
}


def put_brackets_sent(
    brackets_l: Mapping[int, List[int]],
    brackets_r: Mapping[int, List[int]],
    sent_w_dicts: Mapping[int, WordData],
    phrase_dict: Mapping[str, str],
    delete_orth: bool,
    selected_cons: List[str],
) -> str:
    """Render a sentence with brackets around selected constituent types."""
    parts: List[str] = []
    for word_id, word in sent_w_dicts.items():
        for head_id in brackets_l.get(word_id, []):
            phrase = phrase_dict[sent_w_dicts[head_id]['pos']]
            if phrase in selected_cons:
                parts.extend((' [', phrase))
        parts.extend((' ', word['wf']))
        for head_id in brackets_r.get(word_id, []):
            if phrase_dict[sent_w_dicts[head_id]['pos']] in selected_cons:
                parts.append(']')

    bracketed_sentence = ''.join(parts)
    punctuation = '''!()”“’-;:'",.?@_«»…'''
    if delete_orth:
        bracketed_sentence = ''.join(
            character
            for character in bracketed_sentence
            if character not in punctuation
        )
    bracketed_sentence = bracketed_sentence.replace('  ', ' ')

    if '[' not in bracketed_sentence:
        bracketed_sentence = ' ' + one_word_const(sent_w_dicts, phrase_dict)[2]

    return bracketed_sentence[1:]


def select_spec_cons(
    brackets_l: Mapping[int, List[int]],
    brackets_r: Mapping[int, List[int]],
    sent_w_dicts: Mapping[int, WordData],
    phrase_dict: Mapping[str, str],
    selected_cons: List[str],
    emb: bool,
) -> Tuple[List[Dict[int, List[List[Any]]]], Dict[int, str], str]:
    """Select and render spans belonging to requested constituent categories."""
    tags_by_category = {
        category: [tag for tag, phrase in phrase_dict.items() if phrase == category]
        for category in selected_cons
    }
    constituents: Dict[str, Dict[int, List[int]]] = {}

    for category, tags in tags_by_category.items():
        category_constituents: Dict[int, List[int]] = {}
        for left_id, head_ids in brackets_l.items():
            for head_id in head_ids:
                if sent_w_dicts[head_id]['pos'] in tags:
                    category_constituents[head_id] = [left_id]
        constituents[category] = category_constituents

    for category, category_constituents in constituents.items():
        for head_id, span in category_constituents.items():
            for right_id, head_ids in brackets_r.items():
                if head_id in head_ids:
                    span.append(right_id)

    constituents = {
        category: category_constituents
        for category, category_constituents in constituents.items()
        if category_constituents
    }
    if not emb:
        for category, category_constituents in constituents.items():
            non_embedded_ids = [
                head_id
                for head_id, span in category_constituents.items()
                if all(
                    not (
                        head_id >= other_span[0]
                        and head_id <= other_span[1]
                        and span != other_span
                    )
                    for other_span in category_constituents.values()
                )
            ]
            constituents[category] = {
                head_id: span
                for head_id, span in category_constituents.items()
                if head_id in non_embedded_ids
            }

    output_parts: List[str] = []
    output_list: List[Dict[int, List[List[Any]]]] = []
    output_categories: Dict[int, str] = {}
    for category, category_constituents in constituents.items():
        output_parts.append(f'\t{category}s:\n')
        for head_id, span in category_constituents.items():
            output_categories[head_id] = category
            words = [
                [word_id, sent_w_dicts[word_id]['wf']]
                for word_id in range(span[0], span[1] + 1)
            ]
            output_list.append({head_id: words})
            output_parts.extend((''.join(f'{word[1]} ' for word in words), '\n'))

    output = ''.join(output_parts)
    if not output_list:
        output_list, output_categories, output = one_word_const(
            sent_w_dicts, phrase_dict
        )
    return output_list, output_categories, output


def one_word_const(
    sent_w_dicts: Mapping[int, WordData], phrase_dict: Mapping[str, str]
) -> Tuple[List[Dict[int, List[List[Any]]]], Dict[int, str], str]:
    """Return the root word as a fallback one-word constituent."""
    output_list: List[Dict[int, List[List[Any]]]] = []
    output_categories: Dict[int, str] = {}
    output = ''

    for head_id, word in sent_w_dicts.items():
        if word['head_id'] == 0:
            category = phrase_dict[word['pos']]
            dependent = [[word['idw'], word['wf']]]
            output_list.append({head_id: dependent})
            output_categories[head_id] = category
            output = f'[{category} {word["wf"]}]'

    return output_list, output_categories, output


def make_const(
    input: str, # input string if use_parser = True, otherwise input in conllu format
    lang = 'ru', # language parameter in case of parsing: str,
    use_parser = False,  # True - Stanza parser will be at work; False - input in the conllu format: bool,
    delete_orth = False,  # delete orthography from the final tree: bool,
    xps = True,  # return specific phrases separately: bool,
    emb = True,  # returns subconstituents, not only maximal projection, if True: bool,
    h_terminals = ['NOUN', 'PRON', 'PROPN', 'ADV'],  # terminals to be put in brackets w/out dependents: List[str],
    selected_cons = ['NP', 'VP', 'PP', 'AP', 'AdvP', 'NumP', 'PartP', 'CCONJP', 'INTJP', 'Particle', 'SCONJP', 'SYMP', 'XP'],  # when we want only some specific constituents only: List[str],
) -> List[Dep2Con]:
    """Convert input text or a CoNLL-U file into constituency representations."""
    output: List[Dep2Con] = []


    if use_parser:
        import stanza

        pipeline = stanza.Pipeline(lang=lang, processors='tokenize,pos,lemma,depparse')
        sentences = pipeline(input).sentences
    else:
        from pyconll.conllu import conllu

        sentences = conllu.load_from_file(input)

    for index, sentence in enumerate(sentences):
        sent_dict = sent_dict_from_sents(index, sentence, use_parser)
        sent_text, sent_len = len_text(sent_dict)
        sentence_index = sentence.meta.get("text") or index if not use_parser else index
        source = (
            'STANZA'
            if use_parser
            else sentence.meta.get('source', '') if sentence.meta else ''
        )

        sent_w_dicts = rearrange_cop(rearrange_pp(sent_dict))
        head_ids = heads(sent_w_dicts.values())
        const, _ = find_children(head_ids, sent_w_dicts)
        x_phrases: Any = [[], {}]
        correct_dep, error_type = check_head(const, sent_w_dicts)

        if correct_dep and sent_w_dicts:
            brackets_l = post_proc(
                find_brackets_l(sent_w_dicts, const, h_terminals), sent_w_dicts, 0
            )
            brackets_r = post_proc(
                find_brackets_r(sent_w_dicts, const, h_terminals), sent_w_dicts, 1
            )
            sent_parse = put_brackets_sent(
                brackets_l,
                brackets_r,
                sent_w_dicts,
                PHRASE_DICT,
                delete_orth,
                selected_cons,
            )
            if xps:
                x_phrases = select_spec_cons(
                    brackets_l,
                    brackets_r,
                    sent_w_dicts,
                    PHRASE_DICT,
                    selected_cons,
                    emb,
                )
        elif sent_w_dicts:
            print(error_type, sent_text)
            continue
        else:
            print('Parsing failed', sent_text)
            continue

        output.append(
            Dep2Con(
                sent_parse=sent_parse,
                x_phrases=x_phrases,
                sent_dict=sent_dict,
                sent_text=sent_text,
                sent_len=sent_len,
                sentence_index=sentence_index,
                source=source,
            )
        )

    return output
