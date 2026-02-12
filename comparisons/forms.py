from django import forms

from .models import LexicalComparison


class LexicalComparisonForm(forms.ModelForm):
    class Meta:
        model = LexicalComparison
        fields = [
            # Hebrew side (pre-filled, hidden)
            'lexeme', 'hebrew_word', 'hebrew_transliteration',
            'hebrew_root', 'hebrew_meaning',
            # Niger-Congo side (user fills in)
            'language', 'nc_word', 'nc_transliteration', 'nc_meaning',
            'nc_usage_example',
            # Classification
            'category', 'semantic_domain', 'notes',
            # Evidence
            'source_type', 'source_reference',
        ]
        widgets = {
            'lexeme': forms.HiddenInput(),
            'hebrew_word': forms.HiddenInput(),
            'hebrew_transliteration': forms.HiddenInput(),
            'hebrew_root': forms.HiddenInput(),
            'hebrew_meaning': forms.HiddenInput(),
            'nc_word': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. nkosi',
            }),
            'nc_transliteration': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Transliteration (optional)',
            }),
            'nc_meaning': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Meaning in the Niger-Congo language',
            }),
            'nc_usage_example': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Example sentence or context (optional)',
            }),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'semantic_domain': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. kinship, agriculture, worship',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Any additional notes (optional)',
            }),
            'source_type': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. oral tradition, published research',
            }),
            'source_reference': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Citation or reference (optional)',
            }),
        }
