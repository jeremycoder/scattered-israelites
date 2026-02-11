from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Look up a key in a dictionary. Usage: {{ glosses|dict_get:word.strongs_id }}"""
    if d is None:
        return ''
    return d.get(key, '')


@register.filter
def in_set(value, the_set):
    """Check membership in a set. Usage: {% if word.lemma|in_set:comparison_lemmas %}"""
    return value in the_set if the_set else False
