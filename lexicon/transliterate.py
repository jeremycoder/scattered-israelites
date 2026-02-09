"""
Hebrew-to-ASCII transliteration for URL slugs.

Pure Python — no Django imports. Converts pointed Hebrew surface text
(with niqqud, cantillation marks, and morpheme separators) into readable
Latin transliterations suitable for URL slugs.

Usage:
    >>> from lexicon.transliterate import hebrew_to_slug
    >>> hebrew_to_slug('בְּ/רֵאשִׁ֖ית')
    'bereshit'
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Unicode ranges
# ---------------------------------------------------------------------------

# Cantillation marks: U+0591–U+05AF (carry no phonetic info)
_CANTILLATION = set(range(0x0591, 0x05B0))

# Dagesh / mappiq: U+05BC
_DAGESH = '\u05BC'

# Shin / sin dots
_SHIN_DOT = '\u05C1'
_SIN_DOT = '\u05C2'

# Other marks to ignore
_METEG = '\u05BD'       # meteg
_MAQAF = '\u05BE'       # maqaf (Hebrew hyphen)
_RAFE = '\u05BF'        # rafe
_PASEQ = '\u05C0'       # paseq
_SOF_PASUQ = '\u05C3'   # sof pasuq

_IGNORE = {_METEG, _RAFE, _PASEQ, _SOF_PASUQ, '\u05C4', '\u05C5', '\u05C7'}

# ---------------------------------------------------------------------------
# Consonant mappings
# ---------------------------------------------------------------------------

# Letters that change pronunciation with dagesh (begadkephat)
# With dagesh → hard, without → soft
_BGDKPT_HARD = {
    '\u05D1': 'b',   # bet
    '\u05DB': 'k',   # kaf
    '\u05E4': 'p',   # pe
}
_BGDKPT_SOFT = {
    '\u05D1': 'v',   # vet
    '\u05DB': 'kh',  # khaf
    '\u05E4': 'f',   # fe
}

# All consonants (default, without dagesh consideration)
_CONSONANTS = {
    '\u05D0': '',     # aleph — silent
    '\u05D1': 'v',    # bet (soft default)
    '\u05D2': 'g',    # gimel
    '\u05D3': 'd',    # dalet
    '\u05D4': 'h',    # he
    '\u05D5': 'v',    # vav
    '\u05D6': 'z',    # zayin
    '\u05D7': 'ch',   # chet
    '\u05D8': 't',    # tet
    '\u05D9': 'y',    # yod
    '\u05DA': 'kh',   # final kaf
    '\u05DB': 'kh',   # kaf (soft default)
    '\u05DC': 'l',    # lamed
    '\u05DD': 'm',    # final mem
    '\u05DE': 'm',    # mem
    '\u05DF': 'n',    # final nun
    '\u05E0': 'n',    # nun
    '\u05E1': 's',    # samekh
    '\u05E2': '',     # ayin — silent
    '\u05E3': 'f',    # final pe
    '\u05E4': 'f',    # pe (soft default)
    '\u05E5': 'ts',   # final tsade
    '\u05E6': 'ts',   # tsade
    '\u05E7': 'q',    # qof
    '\u05E8': 'r',    # resh
    '\u05E9': 'sh',   # shin (default without dot)
    '\u05EA': 't',    # tav
}

# ---------------------------------------------------------------------------
# Vowel mappings (niqqud)
# ---------------------------------------------------------------------------

_VOWELS = {
    '\u05B0': 'e',    # sheva
    '\u05B1': 'e',    # hataf segol
    '\u05B2': 'a',    # hataf patah
    '\u05B3': 'o',    # hataf qamats
    '\u05B4': 'i',    # hiriq
    '\u05B5': 'e',    # tsere
    '\u05B6': 'e',    # segol
    '\u05B7': 'a',    # patah
    '\u05B8': 'a',    # qamats
    '\u05B9': 'o',    # holam
    '\u05BA': 'o',    # holam haser for vav
    '\u05BB': 'u',    # qubuts
}


def _is_combining(ch):
    """Return True if the character is a combining mark (not a base consonant)."""
    cp = ord(ch)
    # Vowels, cantillation, dagesh, shin/sin dots, other marks
    return 0x0591 <= cp <= 0x05C7


def transliterate_hebrew(text: str) -> str:
    """Convert pointed Hebrew text to a Latin transliteration.

    Handles niqqud (vowel points), cantillation marks, dagesh,
    shin/sin dots, mater lectionis (vav/yod as vowel letters),
    and morpheme separators (/).
    """
    # Strip morpheme separators and maqaf
    text = text.replace('/', '').replace(_MAQAF, '')

    chars = list(text)
    result = []
    i = 0

    while i < len(chars):
        ch = chars[i]
        cp = ord(ch)

        # Skip any combining mark encountered without a preceding consonant
        if _is_combining(ch):
            i += 1
            continue

        # Consonant
        if ch in _CONSONANTS:
            # Collect ALL combining marks that follow this consonant
            has_dagesh = False
            has_shin_dot = False
            has_sin_dot = False
            vowels = []
            j = i + 1
            while j < len(chars) and _is_combining(chars[j]):
                nch = chars[j]
                ncp = ord(nch)
                if nch == _DAGESH:
                    has_dagesh = True
                elif nch == _SHIN_DOT:
                    has_shin_dot = True
                elif nch == _SIN_DOT:
                    has_sin_dot = True
                elif nch in _VOWELS:
                    vowels.append(_VOWELS[nch])
                # else: cantillation or ignorable — skip
                j += 1

            # --- Mater lectionis: vav as vowel carrier ---
            if ch == '\u05D5':  # vav
                if has_dagesh and not vowels:
                    # Shureq (vav + dagesh, no vowel) = "u"
                    result.append('u')
                    i = j
                    continue
                if vowels == ['o']:
                    # Holam male (vav + holam) = "o"
                    result.append('o')
                    i = j
                    continue

            # --- Mater lectionis: yod after hiriq = hiriq male ---
            if ch == '\u05D9' and not vowels:  # yod with no vowels
                # Check if previous output ends with 'i' (hiriq)
                if result and result[-1] == 'i':
                    # Yod is mater lectionis — skip it
                    i = j
                    continue

            # Resolve shin/sin
            if ch == '\u05E9':  # shin
                if has_sin_dot:
                    result.append('s')
                else:
                    result.append('sh')
            # Resolve begadkephat with dagesh
            elif has_dagesh and ch in _BGDKPT_HARD:
                result.append(_BGDKPT_HARD[ch])
            else:
                result.append(_CONSONANTS[ch])

            # Append collected vowels
            result.extend(vowels)
            i = j
            continue

        # Non-Hebrew character (space, digit, etc.) — pass through
        if ch.isalnum():
            result.append(ch)
        i += 1

    return ''.join(result)


def hebrew_to_slug(text: str) -> str:
    """Convert Hebrew surface text to a URL-safe slug.

    Returns a lowercase string containing only [a-z0-9-].
    Returns empty string if the input produces no transliterable content.
    """
    transliterated = transliterate_hebrew(text)
    # Lowercase
    slug = transliterated.lower()
    # Replace any non-alphanumeric with hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug
