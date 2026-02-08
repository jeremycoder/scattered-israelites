from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Look up a key in a dictionary. Usage: {{ glosses|dict_get:word.strongs_id }}"""
    if d is None:
        return ''
    return d.get(key, '')
