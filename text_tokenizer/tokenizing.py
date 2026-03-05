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
_ARM_ONLY = re.compile(r'[^\u0531-\u058F\s]')
_SPACES   = re.compile(r'\s+')

_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        print("⏳ Loading Armenian NLP model...")
        t0 = time.perf_counter()
        _pipeline = stanza.Pipeline(
            'hy',
            processors='tokenize,pos,lemma',
            tokenize_batch_size=64,
            lemma_batch_size=256,
            logging_level='ERROR'
        )
        print(f"✅ Ready in {time.perf_counter() - t0:.1f}s")
    return _pipeline


def parse(text: str) -> str:
    """
    Input:  raw Armenian text
    Output: clean space-joined lemmatized string ready for generate_from_phrase()
    
    Example:
        parse("ես շոկոլադ շատ եմ սիրում")
        → "ես շոկոլադ շատ սիրել"
    """
    text = _CLEAN_RE.sub('', text)
    text = _ARM_ONLY.sub('', text)
    text = _SPACES.sub(' ', text).strip()

    if not text:
        return ''

    doc = _get_pipeline()(text)
    tokens = []
    for sent in doc.sentences:
        for word in sent.words:
            root = (word.lemma or word.text).lower().strip()
            pos  = (word.upos or '').upper()
            if pos == 'AUX' or root in AUX_VERBS:
                continue
            if len(root) > 1:
                tokens.append(root)

    return ' '.join(tokens)


if __name__ == '__main__':
    tests = [
        "ես շոկոլադ շատ եմ սիրում",
        "դու գնում ես տուն",
        "մենք սիրում ենք Հայաստան",
        "Այս դեպքում երկրորդական նախադասությունը գլխավոր նախադասության ստորոգելին է կամ որևէ լրացումը․ Եթե լռեիր, փիլիսոփա կլինեիր։, Նստել էին, ով ինչպես ուզում էր"
    ]
    for text in tests:
        print(f"Input  : {text}")
        print(f"Parsed : {parse(text)}")
        print()