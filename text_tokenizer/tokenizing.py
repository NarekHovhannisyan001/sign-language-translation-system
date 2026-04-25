import os
import re
import time
import stanza

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

AUX_VERBS = frozenset({
    'եմ', 'է', 'ենք', 'եք', 'են',
    'էի', 'էիր', 'էր', 'էինք', 'էիք', 'էին',
})

_CLEAN_RE = re.compile(r'http\S+|@\w+|#\w+|RT')
_ARM_ONLY = re.compile(r'[^\u0531-\u0556\u0561-\u0587\s]')
_SPACES   = re.compile(r'\s+')

_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        # print("\u23f3 Loading Armenian NLP model...")
        t0 = time.perf_counter()
        _pipeline = stanza.Pipeline(
            'hy',
            processors='tokenize,pos,lemma',
            tokenize_batch_size=64,
            lemma_batch_size=256,
            logging_level='ERROR'
        )
        print(f"\u2705 Ready in {time.perf_counter() - t0:.1f}s")
    return _pipeline


def _lemmatize_word(word: str) -> list:
    """Lemmatize a single word, returns list of root tokens (filters aux verbs)."""
    doc = _get_pipeline()(word)
    result = []
    for sent in doc.sentences:
        for w in sent.words:
            root = (w.lemma or w.text).lower().strip()
            pos  = (w.upos or '').upper()
            if pos == 'AUX' or root in AUX_VERBS:
                continue
            if len(root) > 1:
                result.append(root)
    return result


def parse(text: str, known_words: set = None) -> list:
    """
    Input:  raw Armenian text
    Output: LIST of tokens ready for generate_from_phrase()
            Multi-word tokens like '\u0562\u0561\u0580\u0587 \u0571\u0565\u0566' kept as single list items.

    known_words: set of JSON filenames (without .json, lowercase).
                 Words found here are kept as-is, skipping lemmatization.
                 Prevents wrong lemmas like \u056f\u0561\u0569\u057d\u0561->\u056f\u0561\u0569 or \u057f\u0561\u0576\u0571->\u057f\u578f\u0576.

    Example:
        parse("\u056f\u0561\u0569\u057d\u0561 \u0565\u0574 \u056c\u057e\u0561\u576b\u578f\u0582\u0574", known_words={"\u056f\u0561\u0569\u057d\u0561"})
        -> ["\u056f\u0561\u0569\u057d\u0561", "\u056c\u057e\u0561\u576b\u0565\u056c"]
    """
    text = _CLEAN_RE.sub('', text)
    text = _ARM_ONLY.sub('', text)
    text = _SPACES.sub(' ', text).strip()

    if not text:
        return []

    words  = text.split()
    result = []
    i = 0

    while i < len(words):
        # Try two-word match in known_words first
        if known_words and i + 1 < len(words):
            two = (words[i] + ' ' + words[i + 1]).lower()
            if two in known_words:
                result.append(two)
                i += 2
                continue

        # Try single word in known_words
        one = words[i].lower()
        if known_words and one in known_words:
            result.append(one)
            i += 1
            continue

        # Not in known_words — lemmatize
        result.extend(_lemmatize_word(words[i]))
        i += 1

    return result


if __name__ == '__main__':
    import sys
    tests = [
    "գրքով",
    "խնձորից",
    "դասարանում",
    "ընկերոջը",
    "ուսանողների",
    "քաղաքներով",
    "տանը",
    "աշխատանքից",
    "մեքենայով",
    "երեխաների",
    "ուսուցչին",
    "գրասեղանի",
    "ծրագրում",
    "համակարգչով",
    "ճանապարհից",
    "գործարաններում",
    "գիտելիքների",
    "ծառերի",
    "դպրոցում",
    "մարդկանց"
    ]
    parse(tests[0])   # warm up
    print()
    for text in tests:
        tokens = parse(text)
        print(f"Input  : {text}")
        print(f"Tokens : {tokens}")
        print()