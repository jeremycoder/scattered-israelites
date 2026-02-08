"""
Pure-Python parser for OSHB morphology codes.

No Django imports — this module operates on plain strings and returns dataclasses.

OSHB morph code format:  {Language}{Segment1}/{Segment2}/...
  Language: H = Hebrew, A = Aramaic
  Segments separated by '/' are morphemes (prefixes, base, suffixes).

Reference: data/oshb/morphhb-master/parsing/Oshm.xml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

POS_MAP = {
    'A': 'adjective',
    'C': 'conjunction',
    'D': 'adverb',
    'N': 'noun',
    'P': 'pronoun',
    'R': 'preposition',
    'S': 'suffix',
    'T': 'particle',
    'V': 'verb',
}

# Hebrew verb stems (binyanim)
HEBREW_STEM_MAP = {
    'q': 'Qal',
    'N': 'Niphal',
    'p': 'Piel',
    'P': 'Pual',
    'h': 'Hiphil',
    'H': 'Hophal',
    't': 'Hithpael',
    'o': 'Polel',
    'O': 'Polal',
    'r': 'Hithpolel',
    'm': 'Poel',
    'M': 'Poal',
    'k': 'Palel',
    'K': 'Pulal',
    'Q': 'Qal Passive',
    'l': 'Pilpel',
    'L': 'Polpal',
    'f': 'Hithpalpel',
    'D': 'Nithpael',
    'j': 'Pealal',
    'i': 'Pilel',
    'u': 'Hothpaal',
    'c': 'Tiphil',
    'v': 'Hishtaphel',
    'z': 'Hithpoel',
}

# Aramaic verb stems
ARAMAIC_STEM_MAP = {
    'q': 'Peal',
    'Q': 'Peil',
    'u': 'Hithpeel',
    'p': 'Pael',
    'P': 'Ithpaal',
    'M': 'Hithpaal',
    'a': 'Aphel',
    'h': 'Haphel',
    'H': 'Hophal',
    's': 'Saphel',
    'e': 'Shaphel',
    'i': 'Ithpeel',
    't': 'Hishtaphel',
    'v': 'Ishtaphel',
    'r': 'Hithpolel',
    'z': 'Ithpoel',
    'o': 'Polel',
}

VERB_CONJUGATION_MAP = {
    'p': 'perfect',
    'q': 'sequential_perfect',
    'i': 'imperfect',
    'w': 'sequential_imperfect',
    'v': 'imperative',
    'r': 'participle_active',
    's': 'participle_passive',
    'a': 'infinitive_absolute',
    'c': 'infinitive_construct',
    'h': 'cohortative',
    'j': 'jussive',
}

NOUN_TYPE_MAP = {
    'c': 'common',
    'g': 'gentilic',
    'p': 'proper_name',
    'x': None,
}

ADJECTIVE_TYPE_MAP = {
    'a': 'adjective',
    'c': 'cardinal_number',
    'o': 'ordinal_number',
}

PRONOUN_TYPE_MAP = {
    'p': 'personal',
    'd': 'demonstrative',
    'f': 'indefinite',
    'i': 'interrogative',
    'r': 'relative',
    'x': None,
}

PARTICLE_TYPE_MAP = {
    'a': 'affirmation',
    'd': 'definite_article',
    'e': 'exhortation',
    'i': 'interrogative',
    'j': 'interjection',
    'm': 'demonstrative',
    'n': 'negative',
    'o': 'direct_object_marker',
    'r': 'relative',
}

PERSON_MAP = {
    '1': 1,
    '2': 2,
    '3': 3,
    'x': None,
}

GENDER_MAP = {
    'm': 'masculine',
    'f': 'feminine',
    'c': 'common',
    'b': 'both',
    'x': None,
}

NUMBER_MAP = {
    's': 'singular',
    'p': 'plural',
    'd': 'dual',
    'x': None,
}

STATE_MAP = {
    'a': 'absolute',
    'c': 'construct',
    'd': 'determined',
}

# Stems that are inherently passive
PASSIVE_STEMS = {
    'Pual', 'Hophal', 'Qal Passive', 'Polal', 'Poal', 'Pulal',
    'Polpal', 'Hothpaal',
    'Peil',  # Aramaic
}

# Stems that are inherently reflexive/middle
REFLEXIVE_STEMS = {
    'Niphal', 'Hithpael', 'Hithpolel', 'Hithpalpel', 'Nithpael',
    'Hithpoel', 'Hishtaphel',
    'Ithpaal', 'Hithpaal', 'Hithpeel', 'Ithpeel', 'Ishtaphel',
    'Ithpoel',  # Aramaic
}

# Stems that are active/causative
ACTIVE_STEMS = {
    'Qal', 'Piel', 'Hiphil', 'Polel', 'Poel', 'Palel', 'Pilpel',
    'Pilel', 'Pealal', 'Tiphil',
    'Peal', 'Pael', 'Aphel', 'Haphel', 'Saphel', 'Shaphel',  # Aramaic
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedMorph:
    """All parsed fields matching HebrewMorphAnalysis, plus metadata."""

    language: str = ''                              # 'hebrew' or 'aramaic'
    part_of_speech: str = ''                        # verb, noun, etc.
    subtype: Optional[str] = None                   # common, proper_name, adjective, cardinal_number, etc.
    binyan: Optional[str] = None                    # Qal, Niphal, etc.
    conjugation: Optional[str] = None               # perfect, imperfect, etc.
    person: Optional[int] = None                    # 1, 2, 3
    gender: Optional[str] = None                    # masculine, feminine, common, both
    number: Optional[str] = None                    # singular, plural, dual
    state: Optional[str] = None                     # absolute, construct, determined
    aspect: Optional[str] = None                    # perfective, imperfective
    voice: Optional[str] = None                     # active, passive, middle
    mood: Optional[str] = None                      # indicative, imperative, jussive, cohortative
    polarity: Optional[str] = None
    negation_particle: Optional[str] = None
    definiteness: Optional[str] = None              # definite, indefinite
    suffix_person: Optional[int] = None
    suffix_gender: Optional[str] = None
    suffix_number: Optional[str] = None
    has_article: bool = False
    has_pronominal_suffix: bool = False
    has_directional_he: bool = False
    has_paragogic_he: bool = False
    has_paragogic_nun: bool = False
    prefix_pos_list: list = field(default_factory=list)
    raw_code: str = ''
    parse_errors: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Segment classifiers
# ---------------------------------------------------------------------------

def _is_suffix_segment(seg: str) -> bool:
    """Return True if this segment is a suffix (S...) or Aramaic Td."""
    return seg.startswith('S') or seg == 'Td'


def _is_prefix_segment(seg: str) -> bool:
    """Return True if this segment acts as a grammatical prefix."""
    if not seg:
        return False
    first = seg[0]
    # C, D, R are always prefixes; Td (article) is a prefix; Rd (prep+article) is prefix
    if first in ('C', 'D', 'R'):
        return True
    if first == 'T' and len(seg) >= 2:
        return True
    return False


# ---------------------------------------------------------------------------
# POS-specific parsers
# ---------------------------------------------------------------------------

def _parse_verb(seg: str, language: str, result: ParsedMorph) -> None:
    """Parse a verb segment: V[stem][conj][PGN...] or V[stem][r/s][GNS]."""
    result.part_of_speech = 'verb'
    if len(seg) < 2:
        result.parse_errors.append(f'Verb segment too short: {seg}')
        return

    stem_char = seg[1]
    stem_map = ARAMAIC_STEM_MAP if language == 'aramaic' else HEBREW_STEM_MAP
    result.binyan = stem_map.get(stem_char)
    if result.binyan is None:
        result.parse_errors.append(f'Unknown verb stem: {stem_char}')

    if len(seg) < 3:
        return

    conj_char = seg[2]
    conj = VERB_CONJUGATION_MAP.get(conj_char)
    if conj is None:
        result.parse_errors.append(f'Unknown verb conjugation: {conj_char}')
        return
    result.conjugation = conj

    rest = seg[3:]

    # Participles: r/s → [gender][number][state]
    if conj_char in ('r', 's'):
        if len(rest) >= 1:
            result.gender = GENDER_MAP.get(rest[0])
        if len(rest) >= 2:
            result.number = NUMBER_MAP.get(rest[1])
        if len(rest) >= 3:
            result.state = STATE_MAP.get(rest[2])
        return

    # Infinitives: a/c → no PGN (bare)
    if conj_char in ('a', 'c'):
        # Infinitives have no person/gender/number
        return

    # Finite forms: [person][gender][number]
    if len(rest) >= 1:
        result.person = PERSON_MAP.get(rest[0])
    if len(rest) >= 2:
        result.gender = GENDER_MAP.get(rest[1])
    if len(rest) >= 3:
        result.number = NUMBER_MAP.get(rest[2])


def _parse_noun(seg: str, result: ParsedMorph) -> None:
    """Parse a noun segment: N[type][gender][number][state]."""
    result.part_of_speech = 'noun'
    if len(seg) < 2:
        result.parse_errors.append(f'Noun segment too short: {seg}')
        return

    ntype = seg[1]
    result.subtype = NOUN_TYPE_MAP.get(ntype)
    if ntype not in NOUN_TYPE_MAP:
        result.parse_errors.append(f'Unknown noun type: {ntype}')

    # Proper nouns have no further morphological fields
    if ntype == 'p':
        return

    if len(seg) >= 3:
        result.gender = GENDER_MAP.get(seg[2])
    if len(seg) >= 4:
        result.number = NUMBER_MAP.get(seg[3])
    if len(seg) >= 5:
        result.state = STATE_MAP.get(seg[4])


def _parse_adjective(seg: str, result: ParsedMorph) -> None:
    """Parse an adjective segment: A[type][gender][number][state]."""
    result.part_of_speech = 'adjective'
    if len(seg) < 2:
        result.parse_errors.append(f'Adjective segment too short: {seg}')
        return

    atype = seg[1]
    result.subtype = ADJECTIVE_TYPE_MAP.get(atype)
    if atype not in ADJECTIVE_TYPE_MAP:
        result.parse_errors.append(f'Unknown adjective type: {atype}')

    if len(seg) >= 3:
        result.gender = GENDER_MAP.get(seg[2])
    if len(seg) >= 4:
        result.number = NUMBER_MAP.get(seg[3])
    if len(seg) >= 5:
        result.state = STATE_MAP.get(seg[4])


def _parse_pronoun(seg: str, result: ParsedMorph) -> None:
    """Parse a pronoun segment: P[type][person][gender][number]."""
    result.part_of_speech = 'pronoun'
    if len(seg) < 2:
        result.parse_errors.append(f'Pronoun segment too short: {seg}')
        return

    ptype = seg[1]
    result.subtype = PRONOUN_TYPE_MAP.get(ptype)
    if ptype not in PRONOUN_TYPE_MAP:
        result.parse_errors.append(f'Unknown pronoun type: {ptype}')

    # Indefinite pronouns (f) have no further fields
    if ptype == 'f':
        return

    if len(seg) >= 3:
        result.person = PERSON_MAP.get(seg[2])
    if len(seg) >= 4:
        result.gender = GENDER_MAP.get(seg[3])
    if len(seg) >= 5:
        result.number = NUMBER_MAP.get(seg[4])


def _parse_particle(seg: str, result: ParsedMorph) -> None:
    """Parse a particle segment: T[type]. Bare 'T' = unspecified particle."""
    result.part_of_speech = 'particle'
    if len(seg) < 2:
        # Bare particle with no subtype (e.g. Aramaic 'AT')
        return

    ttype = seg[1]
    result.subtype = PARTICLE_TYPE_MAP.get(ttype)
    if ttype not in PARTICLE_TYPE_MAP:
        result.parse_errors.append(f'Unknown particle type: {ttype}')


def _parse_suffix(seg: str, result: ParsedMorph) -> None:
    """Parse a suffix segment: Sp[person][gender][number], Sd, Sh, Sn."""
    if len(seg) < 2:
        result.parse_errors.append(f'Suffix segment too short: {seg}')
        return

    stype = seg[1]
    if stype == 'd':
        result.has_directional_he = True
    elif stype == 'h':
        result.has_paragogic_he = True
    elif stype == 'n':
        result.has_paragogic_nun = True
    elif stype == 'p':
        result.has_pronominal_suffix = True
        if len(seg) >= 3:
            result.suffix_person = PERSON_MAP.get(seg[2])
        if len(seg) >= 4:
            result.suffix_gender = GENDER_MAP.get(seg[3])
        if len(seg) >= 5:
            result.suffix_number = NUMBER_MAP.get(seg[4])
    else:
        result.parse_errors.append(f'Unknown suffix type: {stype}')


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------

def _derive_fields(result: ParsedMorph) -> None:
    """Compute aspect, voice, mood, definiteness from parsed fields."""

    # Aspect
    if result.conjugation in ('perfect', 'sequential_perfect'):
        result.aspect = 'perfective'
    elif result.conjugation in ('imperfect', 'sequential_imperfect',
                                 'cohortative', 'jussive'):
        result.aspect = 'imperfective'

    # Voice
    if result.binyan:
        if result.binyan in PASSIVE_STEMS:
            result.voice = 'passive'
        elif result.binyan in REFLEXIVE_STEMS:
            result.voice = 'middle'
        elif result.binyan in ACTIVE_STEMS:
            result.voice = 'active'

    # Also: participle_passive in active stems → passive voice
    if result.conjugation == 'participle_passive' and result.voice == 'active':
        result.voice = 'passive'

    # Mood
    if result.conjugation == 'imperative':
        result.mood = 'imperative'
    elif result.conjugation == 'cohortative':
        result.mood = 'cohortative'
    elif result.conjugation == 'jussive':
        result.mood = 'jussive'
    elif result.conjugation in ('perfect', 'imperfect', 'sequential_perfect',
                                 'sequential_imperfect'):
        result.mood = 'indicative'

    # Definiteness
    if result.has_article:
        result.definiteness = 'definite'
    elif result.state == 'determined':
        result.definiteness = 'definite'
    elif result.part_of_speech == 'noun' and result.subtype == 'proper_name':
        result.definiteness = 'definite'
    elif result.has_pronominal_suffix and result.part_of_speech != 'verb':
        result.definiteness = 'definite'
    elif result.state == 'construct':
        # Construct nouns derive definiteness from the nomen rectum;
        # we can't tell from the code alone, so leave as None.
        pass
    elif result.part_of_speech in ('noun', 'adjective'):
        result.definiteness = 'indefinite'


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_morph(code: str) -> ParsedMorph:
    """
    Parse an OSHB morphology code into structured fields.

    Examples:
        parse_morph('HVqp3ms')  → Qal perfect 3ms
        parse_morph('HR/Ncfsa') → preposition + noun common feminine singular absolute
        parse_morph('HC/Vqw3ms') → conjunction + Qal wayyiqtol 3ms
    """
    result = ParsedMorph(raw_code=code)

    if not code:
        result.parse_errors.append('Empty morph code')
        return result

    # 1. Extract language
    lang_char = code[0]
    if lang_char == 'H':
        result.language = 'hebrew'
    elif lang_char == 'A':
        result.language = 'aramaic'
    else:
        result.parse_errors.append(f'Unknown language prefix: {lang_char}')
        result.language = 'hebrew'  # fallback

    remainder = code[1:]
    if not remainder:
        result.parse_errors.append('No segments after language prefix')
        return result

    # 2. Split on '/' to get segments
    segments = remainder.split('/')

    # Filter out empty segments (e.g. trailing slash)
    segments = [s for s in segments if s]
    if not segments:
        result.parse_errors.append('No valid segments found')
        return result

    # 3. Classify segments right-to-left: suffixes, then base, rest are prefixes
    suffixes = []
    non_suffix = []

    # Walk from the right; anything starting with 'S' or exactly 'Td' is a suffix
    for seg in reversed(segments):
        if _is_suffix_segment(seg) and len(non_suffix) == 0:
            # Only collect consecutive trailing suffixes
            suffixes.insert(0, seg)
        else:
            non_suffix.insert(0, seg)

    # If all segments were classified as suffixes, pull the first one back
    # as the base (e.g. standalone 'Td' for the definite article).
    if not non_suffix:
        non_suffix.append(suffixes.pop(0))
    if not non_suffix:
        result.parse_errors.append('No base segment found')
        return result

    # Base = last non-suffix segment; everything before it = prefixes
    prefixes = non_suffix[:-1]
    base = non_suffix[-1]

    # 4. Process prefixes
    for pfx in prefixes:
        pos_char = pfx[0] if pfx else ''
        pos_name = POS_MAP.get(pos_char, pos_char)
        result.prefix_pos_list.append(pos_name)

        # Check for article-bearing prefixes
        if pfx == 'Td':
            result.has_article = True
        elif pos_char == 'T' and len(pfx) >= 2 and pfx[1] == 'd':
            result.has_article = True
        elif pos_char == 'R' and len(pfx) >= 2 and pfx[1] == 'd':
            # Rd = preposition + definite article fused
            result.has_article = True

    # 5. Dispatch base segment to POS-specific parser
    base_pos = base[0] if base else ''
    if base_pos == 'V':
        _parse_verb(base, result.language, result)
    elif base_pos == 'N':
        _parse_noun(base, result)
    elif base_pos == 'A':
        _parse_adjective(base, result)
    elif base_pos == 'P':
        _parse_pronoun(base, result)
    elif base_pos == 'T':
        _parse_particle(base, result)
    elif base_pos == 'C':
        result.part_of_speech = 'conjunction'
    elif base_pos == 'D':
        result.part_of_speech = 'adverb'
    elif base_pos == 'R':
        result.part_of_speech = 'preposition'
    elif base_pos == 'S':
        # Rare: suffix is the base (shouldn't normally happen)
        _parse_suffix(base, result)
    else:
        result.parse_errors.append(f'Unknown base POS: {base_pos}')

    # 6. Process suffix segments
    for sfx in suffixes:
        if sfx == 'Td':
            # Aramaic determined article suffix
            result.state = 'determined'
        elif sfx.startswith('S'):
            _parse_suffix(sfx, result)

    # 7. Derive aspect, voice, mood, definiteness
    _derive_fields(result)

    return result
