"""Tests for the Hebrew transliteration module."""

import unittest

from lexicon.transliterate import hebrew_to_slug, transliterate_hebrew


class TestTransliterateHebrew(unittest.TestCase):
    """Test transliterate_hebrew produces readable Latin output."""

    def test_bereshit(self):
        # בְּרֵאשִׁית with morpheme separator and cantillation
        self.assertEqual(transliterate_hebrew('בְּ/רֵאשִׁ֖ית'), 'bereshit')

    def test_bara(self):
        # בָּרָא with dagesh in bet + qamats
        self.assertEqual(transliterate_hebrew('בָּרָ֣א'), 'bara')

    def test_elohim(self):
        # אֱלֹהִים with hataf segol + holam + hiriq
        self.assertEqual(transliterate_hebrew('אֱלֹהִ֑ים'), 'elohim')

    def test_hashamayim(self):
        # הַשָּׁמַיִם with article + dagesh + shin dot
        self.assertEqual(transliterate_hebrew('הַ/שָּׁמַ֖יִם'), 'hashamayim')

    def test_veet(self):
        # וְאֵת — vav + sheva + aleph + tsere + tav
        self.assertEqual(transliterate_hebrew('וְ/אֵ֥ת'), 'veet')

    def test_haarets(self):
        # הָאָרֶץ — he + qamats + aleph + qamats + resh + segol + final tsade
        self.assertEqual(transliterate_hebrew('הָ/אָֽרֶץ'), 'haarets')

    def test_shin_vs_sin(self):
        # shin dot → sh
        self.assertEqual(transliterate_hebrew('שָׁלוֹם'), 'shalom')

    def test_sin_dot(self):
        # sin dot → s
        self.assertEqual(transliterate_hebrew('שָׂרָה'), 'sarah')

    def test_shin_default(self):
        # shin without dot defaults to sh
        self.assertEqual(transliterate_hebrew('שׁ'), 'sh')

    def test_dagesh_bet(self):
        # בּ (bet with dagesh) → b
        self.assertEqual(transliterate_hebrew('בּ'), 'b')

    def test_soft_bet(self):
        # ב (bet without dagesh) → v
        self.assertEqual(transliterate_hebrew('ב'), 'v')

    def test_dagesh_kaf(self):
        # כּ (kaf with dagesh) → k
        self.assertEqual(transliterate_hebrew('כּ'), 'k')

    def test_soft_kaf(self):
        # כ (kaf without dagesh) → kh
        self.assertEqual(transliterate_hebrew('כ'), 'kh')

    def test_dagesh_pe(self):
        # פּ (pe with dagesh) → p
        self.assertEqual(transliterate_hebrew('פּ'), 'p')

    def test_soft_pe(self):
        # פ (pe without dagesh) → f
        self.assertEqual(transliterate_hebrew('פ'), 'f')

    def test_final_forms(self):
        self.assertIn('kh', transliterate_hebrew('ך'))  # final kaf
        self.assertIn('m', transliterate_hebrew('ם'))    # final mem
        self.assertIn('n', transliterate_hebrew('ן'))    # final nun
        self.assertIn('f', transliterate_hebrew('ף'))    # final pe
        self.assertIn('ts', transliterate_hebrew('ץ'))   # final tsade

    def test_all_vowels(self):
        # Each vowel on its own after bet
        self.assertEqual(transliterate_hebrew('בְ'), 've')   # sheva
        self.assertEqual(transliterate_hebrew('בֱ'), 've')   # hataf segol
        self.assertEqual(transliterate_hebrew('בֲ'), 'va')   # hataf patah
        self.assertEqual(transliterate_hebrew('בֳ'), 'vo')   # hataf qamats
        self.assertEqual(transliterate_hebrew('בִ'), 'vi')   # hiriq
        self.assertEqual(transliterate_hebrew('בֵ'), 've')   # tsere
        self.assertEqual(transliterate_hebrew('בֶ'), 've')   # segol
        self.assertEqual(transliterate_hebrew('בַ'), 'va')   # patah
        self.assertEqual(transliterate_hebrew('בָ'), 'va')   # qamats
        self.assertEqual(transliterate_hebrew('בֹ'), 'vo')   # holam
        self.assertEqual(transliterate_hebrew('בֻ'), 'vu')   # qubuts

    def test_silent_letters(self):
        # aleph and ayin are silent
        self.assertEqual(transliterate_hebrew('א'), '')
        self.assertEqual(transliterate_hebrew('ע'), '')

    def test_empty_input(self):
        self.assertEqual(transliterate_hebrew(''), '')

    def test_morpheme_separator_stripped(self):
        # Separator should not appear in output
        result = transliterate_hebrew('בְּ/רֵאשִׁית')
        self.assertNotIn('/', result)

    def test_cantillation_stripped(self):
        # With and without cantillation should give same result
        with_cant = transliterate_hebrew('בָּרָ֣א')
        without = transliterate_hebrew('בָּרָא')
        self.assertEqual(with_cant, without)


class TestHebrewToSlug(unittest.TestCase):
    """Test hebrew_to_slug produces URL-safe slugs."""

    def test_bereshit_slug(self):
        self.assertEqual(hebrew_to_slug('בְּ/רֵאשִׁ֖ית'), 'bereshit')

    def test_bara_slug(self):
        self.assertEqual(hebrew_to_slug('בָּרָ֣א'), 'bara')

    def test_elohim_slug(self):
        self.assertEqual(hebrew_to_slug('אֱלֹהִ֑ים'), 'elohim')

    def test_slug_is_lowercase(self):
        slug = hebrew_to_slug('בְּרֵאשִׁית')
        self.assertEqual(slug, slug.lower())

    def test_slug_only_valid_chars(self):
        slug = hebrew_to_slug('הַ/שָּׁמַ֖יִם')
        self.assertTrue(all(c.isalnum() or c == '-' for c in slug))

    def test_empty_input_returns_empty(self):
        self.assertEqual(hebrew_to_slug(''), '')

    def test_no_leading_trailing_hyphens(self):
        slug = hebrew_to_slug('וְ/אֵ֥ת')
        self.assertFalse(slug.startswith('-'))
        self.assertFalse(slug.endswith('-'))


if __name__ == '__main__':
    unittest.main()
