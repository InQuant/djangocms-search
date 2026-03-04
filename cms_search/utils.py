# -*- coding: utf-8 -*-
import importlib
import re

import nh3
from django.db import models


def clean_join(separator, iterable):
    """
    Filters out iterable to only join non empty items.
    """
    return separator.join(filter(None, iterable))


def get_callable(string_or_callable):
    """
    If given a callable then it returns it, otherwise it resolves the path
    and returns an object.
    """
    if callable(string_or_callable):
        return string_or_callable
    else:
        module_name, object_name = string_or_callable.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, object_name)


def get_field_value(obj, name):
    """
    Given a model instance and a field name (or attribute),
    returns the value of the field or an empty string.
    """
    fields = name.split('__')

    name = fields[0]

    try:
        obj._meta.get_field(name)
    except (AttributeError, models.FieldDoesNotExist):
        # we catch attribute error because obj will not always be a model
        # specially when going through multiple relationships.
        value = getattr(obj, name, None) or ''
    else:
        value = getattr(obj, name)

    if len(fields) > 1:
        remaining = '__'.join(fields[1:])
        return get_field_value(value, remaining)
    return value


_LINK_RE = re.compile(
    r'<a\s[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def strip_tags(value):
    """Strip all HTML tags, scripts, and styles from value using nh3.
    Preserves link URLs as inline text before stripping."""
    if isinstance(value, str):
        from html import unescape
        # Convert <a href="url">text</a> → text (url) before stripping
        value = _LINK_RE.sub(r'\2 (\1)', value)
        text = nh3.clean(value, tags=set())
        # Decode HTML entities (e.g. &amp; → &) so URLs stay clean
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    return value
