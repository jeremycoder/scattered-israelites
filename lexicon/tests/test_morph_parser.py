"""
Unit tests for lexicon.morph_parser.parse_morph().
"""

import unittest
from lexicon.morph_parser import parse_morph


class TestLanguageDetection(unittest.TestCase):
    def test_hebrew(self):
        r = parse_morph('HNcmsa')
        self.assertEqual(r.language, 'hebrew')

    def test_aramaic(self):
        r = parse_morph('ANcmsa')
        self.assertEqual(r.language, 'aramaic')

    def test_unknown_language(self):
        r = parse_morph('XNcmsa')
        self.assertTrue(len(r.parse_errors) > 0)


class TestEmptyAndMalformed(unittest.TestCase):
    def test_empty_code(self):
        r = parse_morph('')
        self.assertIn('Empty morph code', r.parse_errors)

    def test_language_only(self):
        r = parse_morph('H')
        self.assertIn('No segments after language prefix', r.parse_errors)


class TestVerbs(unittest.TestCase):
    def test_qal_perfect_3ms(self):
        """Gen 1:1 word 2 (בָּרָא) — HVqp3ms."""
        r = parse_morph('HVqp3ms')
        self.assertEqual(r.part_of_speech, 'verb')
        self.assertEqual(r.binyan, 'Qal')
        self.assertEqual(r.conjugation, 'perfect')
        self.assertEqual(r.person, 3)
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.aspect, 'perfective')
        self.assertEqual(r.voice, 'active')
        self.assertEqual(r.mood, 'indicative')

    def test_niphal_imperfect_3fs(self):
        r = parse_morph('HVNi3fs')
        self.assertEqual(r.binyan, 'Niphal')
        self.assertEqual(r.conjugation, 'imperfect')
        self.assertEqual(r.person, 3)
        self.assertEqual(r.gender, 'feminine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.voice, 'middle')
        self.assertEqual(r.aspect, 'imperfective')

    def test_piel_imperative_2ms(self):
        r = parse_morph('HVpv2ms')
        self.assertEqual(r.binyan, 'Piel')
        self.assertEqual(r.conjugation, 'imperative')
        self.assertEqual(r.mood, 'imperative')
        self.assertEqual(r.person, 2)

    def test_hiphil_jussive_3ms(self):
        r = parse_morph('HVhj3ms')
        self.assertEqual(r.binyan, 'Hiphil')
        self.assertEqual(r.conjugation, 'jussive')
        self.assertEqual(r.mood, 'jussive')

    def test_hithpael_perfect_3cp(self):
        r = parse_morph('HVtp3cp')
        self.assertEqual(r.binyan, 'Hithpael')
        self.assertEqual(r.conjugation, 'perfect')
        self.assertEqual(r.voice, 'middle')

    def test_qal_cohortative_1cs(self):
        r = parse_morph('HVqh1cs')
        self.assertEqual(r.conjugation, 'cohortative')
        self.assertEqual(r.mood, 'cohortative')
        self.assertEqual(r.person, 1)
        self.assertEqual(r.gender, 'common')
        self.assertEqual(r.number, 'singular')

    def test_hophal_participle_passive_msa(self):
        r = parse_morph('HVHsmsa')
        self.assertEqual(r.binyan, 'Hophal')
        self.assertEqual(r.conjugation, 'participle_passive')
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.state, 'absolute')
        self.assertIsNone(r.person)  # participles have no person
        self.assertEqual(r.voice, 'passive')

    def test_qal_participle_active_msa(self):
        r = parse_morph('HVqrmsa')
        self.assertEqual(r.conjugation, 'participle_active')
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.state, 'absolute')
        self.assertIsNone(r.person)

    def test_qal_infinitive_construct(self):
        r = parse_morph('HVqc')
        self.assertEqual(r.conjugation, 'infinitive_construct')
        self.assertIsNone(r.person)
        self.assertIsNone(r.gender)
        self.assertIsNone(r.number)

    def test_qal_infinitive_absolute(self):
        r = parse_morph('HVqa')
        self.assertEqual(r.conjugation, 'infinitive_absolute')

    def test_pual_perfect_3ms(self):
        r = parse_morph('HVPp3ms')
        self.assertEqual(r.binyan, 'Pual')
        self.assertEqual(r.voice, 'passive')

    def test_qal_passive_participle_in_active_stem(self):
        """Qal participle passive should override active voice to passive."""
        r = parse_morph('HVqsmsa')
        self.assertEqual(r.binyan, 'Qal')
        self.assertEqual(r.conjugation, 'participle_passive')
        self.assertEqual(r.voice, 'passive')


class TestWayyiqtolSequential(unittest.TestCase):
    def test_wayyiqtol_with_conjunction(self):
        """HC/Vqw3ms — conjunction + qal sequential imperfect 3ms."""
        r = parse_morph('HC/Vqw3ms')
        self.assertEqual(r.part_of_speech, 'verb')
        self.assertEqual(r.binyan, 'Qal')
        self.assertEqual(r.conjugation, 'sequential_imperfect')
        self.assertEqual(r.person, 3)
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')
        self.assertIn('conjunction', r.prefix_pos_list)
        self.assertEqual(r.aspect, 'imperfective')

    def test_sequential_perfect_with_conjunction(self):
        """HC/Vqq2ms — conjunction + qal sequential perfect 2ms."""
        r = parse_morph('HC/Vqq2ms')
        self.assertEqual(r.conjugation, 'sequential_perfect')
        self.assertEqual(r.aspect, 'perfective')


class TestNouns(unittest.TestCase):
    def test_common_noun_feminine_singular_absolute(self):
        r = parse_morph('HNcfsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertEqual(r.subtype, 'common')
        self.assertEqual(r.gender, 'feminine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.state, 'absolute')
        self.assertEqual(r.definiteness, 'indefinite')

    def test_common_noun_masculine_plural_construct(self):
        r = parse_morph('HNcmpc')
        self.assertEqual(r.state, 'construct')
        self.assertIsNone(r.definiteness)  # construct depends on nomen rectum

    def test_common_noun_both_dual_absolute(self):
        r = parse_morph('HNcbda')
        self.assertEqual(r.gender, 'both')
        self.assertEqual(r.number, 'dual')

    def test_proper_noun(self):
        """HNp — proper nouns have no gender/number/state."""
        r = parse_morph('HNp')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertEqual(r.subtype, 'proper_name')
        self.assertIsNone(r.gender)
        self.assertIsNone(r.number)
        self.assertIsNone(r.state)
        self.assertEqual(r.definiteness, 'definite')

    def test_gentilic_noun(self):
        r = parse_morph('HNgmsa')
        self.assertEqual(r.subtype, 'gentilic')


class TestAdjectives(unittest.TestCase):
    def test_adjective_masculine_singular_absolute(self):
        r = parse_morph('HAamsa')
        self.assertEqual(r.part_of_speech, 'adjective')
        self.assertEqual(r.subtype, 'adjective')
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')
        self.assertEqual(r.state, 'absolute')

    def test_cardinal_number(self):
        r = parse_morph('HAcfsa')
        self.assertEqual(r.subtype, 'cardinal_number')

    def test_ordinal_number(self):
        r = parse_morph('HAomsa')
        self.assertEqual(r.subtype, 'ordinal_number')


class TestPronouns(unittest.TestCase):
    def test_personal_pronoun_3ms(self):
        r = parse_morph('HPp3ms')
        self.assertEqual(r.part_of_speech, 'pronoun')
        self.assertEqual(r.subtype, 'personal')
        self.assertEqual(r.person, 3)
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')

    def test_demonstrative_pronoun_x_person(self):
        """HPdxms — demonstrative, person is 'x' → None."""
        r = parse_morph('HPdxms')
        self.assertEqual(r.subtype, 'demonstrative')
        self.assertIsNone(r.person)
        self.assertEqual(r.gender, 'masculine')
        self.assertEqual(r.number, 'singular')

    def test_indefinite_pronoun(self):
        r = parse_morph('HPf')
        self.assertEqual(r.subtype, 'indefinite')
        self.assertIsNone(r.person)

    def test_relative_pronoun(self):
        """Aramaic relative pronoun."""
        r = parse_morph('APr')
        self.assertEqual(r.subtype, 'relative')
        self.assertEqual(r.language, 'aramaic')

    def test_interrogative_pronoun(self):
        r = parse_morph('APi')
        self.assertEqual(r.subtype, 'interrogative')


class TestParticles(unittest.TestCase):
    def test_definite_article(self):
        r = parse_morph('HTd')
        self.assertEqual(r.part_of_speech, 'particle')
        self.assertEqual(r.subtype, 'definite_article')

    def test_negative_particle(self):
        r = parse_morph('HTn')
        self.assertEqual(r.subtype, 'negative')

    def test_interrogative_particle(self):
        r = parse_morph('HTi')
        self.assertEqual(r.subtype, 'interrogative')

    def test_object_marker(self):
        r = parse_morph('HTo')
        self.assertEqual(r.subtype, 'direct_object_marker')

    def test_relative_particle(self):
        r = parse_morph('HTr')
        self.assertEqual(r.subtype, 'relative')


class TestSimplePOS(unittest.TestCase):
    def test_conjunction(self):
        r = parse_morph('HC')
        self.assertEqual(r.part_of_speech, 'conjunction')

    def test_adverb(self):
        r = parse_morph('HD')
        self.assertEqual(r.part_of_speech, 'adverb')

    def test_preposition(self):
        r = parse_morph('HR')
        self.assertEqual(r.part_of_speech, 'preposition')


class TestPrefixes(unittest.TestCase):
    def test_article_prefix_noun(self):
        """HTd/Ncmsa — article prefix makes noun definite."""
        r = parse_morph('HTd/Ncmsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertTrue(r.has_article)
        self.assertEqual(r.definiteness, 'definite')
        self.assertIn('particle', r.prefix_pos_list)

    def test_conjunction_prefix(self):
        r = parse_morph('HC/Ncfsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertIn('conjunction', r.prefix_pos_list)

    def test_preposition_with_article(self):
        """HRd/Ncmsa — preposition+article fused prefix."""
        r = parse_morph('HRd/Ncmsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertTrue(r.has_article)
        self.assertEqual(r.definiteness, 'definite')
        self.assertIn('preposition', r.prefix_pos_list)

    def test_multiple_prefixes(self):
        """HC/R/Ncbsc/Sp3ms — conjunction + preposition + noun + suffix."""
        r = parse_morph('HC/R/Ncbsc/Sp3ms')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertEqual(len(r.prefix_pos_list), 2)
        self.assertIn('conjunction', r.prefix_pos_list)
        self.assertIn('preposition', r.prefix_pos_list)
        self.assertTrue(r.has_pronominal_suffix)
        self.assertEqual(r.suffix_person, 3)
        self.assertEqual(r.suffix_gender, 'masculine')
        self.assertEqual(r.suffix_number, 'singular')
        self.assertEqual(r.definiteness, 'definite')  # pronominal suffix


class TestSuffixes(unittest.TestCase):
    def test_pronominal_suffix_on_noun(self):
        r = parse_morph('HNcmsc/Sp1cs')
        self.assertTrue(r.has_pronominal_suffix)
        self.assertEqual(r.suffix_person, 1)
        self.assertEqual(r.suffix_gender, 'common')
        self.assertEqual(r.suffix_number, 'singular')
        self.assertEqual(r.definiteness, 'definite')

    def test_directional_he(self):
        r = parse_morph('HNcbsa/Sd')
        self.assertTrue(r.has_directional_he)

    def test_paragogic_he(self):
        r = parse_morph('HNcbsa/Sh')
        self.assertTrue(r.has_paragogic_he)

    def test_paragogic_nun(self):
        r = parse_morph('HVqi2fs/Sn')
        self.assertTrue(r.has_paragogic_nun)
        self.assertEqual(r.part_of_speech, 'verb')

    def test_pronominal_suffix_on_verb(self):
        r = parse_morph('HVqp3ms/Sp3fs')
        self.assertTrue(r.has_pronominal_suffix)
        self.assertEqual(r.suffix_person, 3)
        self.assertEqual(r.suffix_gender, 'feminine')
        self.assertEqual(r.suffix_number, 'singular')
        # Verb with suffix — definiteness should not be set
        self.assertIsNone(r.definiteness)

    def test_suffix_on_infinitive_construct(self):
        r = parse_morph('HVqc/Sp3ms')
        self.assertEqual(r.conjugation, 'infinitive_construct')
        self.assertTrue(r.has_pronominal_suffix)


class TestAramaic(unittest.TestCase):
    def test_aramaic_peal_perfect_3ms(self):
        r = parse_morph('AVqp3ms')
        self.assertEqual(r.language, 'aramaic')
        self.assertEqual(r.binyan, 'Peal')  # 'q' in Aramaic = Peal
        self.assertEqual(r.conjugation, 'perfect')

    def test_aramaic_determined_state_via_td(self):
        """ANcmsd/Td — Aramaic noun with determined suffix."""
        r = parse_morph('ANcmsd/Td')
        self.assertEqual(r.language, 'aramaic')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertEqual(r.state, 'determined')
        self.assertEqual(r.definiteness, 'definite')

    def test_aramaic_haphel(self):
        r = parse_morph('AVhp3ms')
        self.assertEqual(r.binyan, 'Haphel')

    def test_aramaic_aphel(self):
        r = parse_morph('AVap3ms')
        self.assertEqual(r.binyan, 'Aphel')

    def test_aramaic_adjective_determined(self):
        r = parse_morph('AAamsd/Td')
        self.assertEqual(r.language, 'aramaic')
        self.assertEqual(r.part_of_speech, 'adjective')
        self.assertEqual(r.state, 'determined')
        self.assertEqual(r.definiteness, 'definite')


class TestXPlaceholders(unittest.TestCase):
    def test_x_gender_is_none(self):
        r = parse_morph('HNcxsa')
        self.assertIsNone(r.gender)

    def test_x_number_is_none(self):
        r = parse_morph('HNcmxa')
        self.assertIsNone(r.number)

    def test_x_person_is_none(self):
        r = parse_morph('HPdxms')
        self.assertIsNone(r.person)


class TestRawCode(unittest.TestCase):
    def test_raw_code_preserved(self):
        r = parse_morph('HVqp3ms')
        self.assertEqual(r.raw_code, 'HVqp3ms')


class TestComplexCompounds(unittest.TestCase):
    def test_conj_article_noun(self):
        """HC/Td/Ncmsa — conjunction + article + noun."""
        r = parse_morph('HC/Td/Ncmsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertTrue(r.has_article)
        self.assertEqual(r.definiteness, 'definite')
        self.assertEqual(len(r.prefix_pos_list), 2)

    def test_conj_prep_article_noun(self):
        """HC/Rd/Ncfsa — conjunction + preposition-article + noun."""
        r = parse_morph('HC/Rd/Ncfsa')
        self.assertEqual(r.part_of_speech, 'noun')
        self.assertTrue(r.has_article)
        self.assertEqual(r.definiteness, 'definite')

    def test_article_participle(self):
        """HTd/Vqrmsa — article + qal participle active."""
        r = parse_morph('HTd/Vqrmsa')
        self.assertEqual(r.part_of_speech, 'verb')
        self.assertEqual(r.conjugation, 'participle_active')
        self.assertTrue(r.has_article)
        self.assertEqual(r.definiteness, 'definite')

    def test_no_errors_on_common_codes(self):
        """A selection of common codes should parse without errors."""
        codes = [
            'HVqp3ms', 'HNcfsa', 'HC', 'HR', 'HD', 'HTd',
            'HVNi3fs', 'HAamsa', 'HPp3ms', 'HPdxfs',
            'HC/Vqw3ms', 'HTd/Ncmsa', 'HNcmsc/Sp3ms',
            'HNcbsa/Sd', 'HVqa', 'HVqc', 'ANcmsa',
        ]
        for code in codes:
            r = parse_morph(code)
            self.assertEqual(r.parse_errors, [], f'Unexpected errors for {code}: {r.parse_errors}')


class TestDerivedFields(unittest.TestCase):
    def test_perfect_is_perfective(self):
        r = parse_morph('HVqp3ms')
        self.assertEqual(r.aspect, 'perfective')

    def test_imperfect_is_imperfective(self):
        r = parse_morph('HVqi3ms')
        self.assertEqual(r.aspect, 'imperfective')

    def test_infinitive_no_aspect(self):
        r = parse_morph('HVqc')
        self.assertIsNone(r.aspect)

    def test_participle_no_aspect(self):
        r = parse_morph('HVqrmsa')
        self.assertIsNone(r.aspect)

    def test_niphal_is_middle_voice(self):
        r = parse_morph('HVNp3ms')
        self.assertEqual(r.voice, 'middle')

    def test_hiphil_is_active_voice(self):
        r = parse_morph('HVhp3ms')
        self.assertEqual(r.voice, 'active')

    def test_hophal_is_passive_voice(self):
        r = parse_morph('HVHp3ms')
        self.assertEqual(r.voice, 'passive')


if __name__ == '__main__':
    unittest.main()
