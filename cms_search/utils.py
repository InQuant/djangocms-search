# -*- coding: utf-8 -*-
import importlib
import re

from django.db import models
from django.utils.encoding import force_str

from lxml.etree import ParseError, ParserError
from lxml_html_clean import Cleaner as LxmlCleaner


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


def _strip_tags(value):
    """
    Returns the given HTML with all tags stripped.
    This is a copy of django.utils.html.strip_tags, except that it adds some
    whitespace in between replaced tags to make sure words are not erroneously
    concatenated.
    """
    return re.sub(r'<[^>]*?>', ' ', force_str(value))


def strip_tags(value):
    """
    Returns the given HTML with all tags stripped.
    We use lxml to strip all js tags and then hand the result to django's
    strip tags. If value isn't valid, just return value since there is
    no tags to strip.
    """
    if isinstance(value, str):
        value = value.strip()

        try:
            partial_strip = LxmlCleaner().clean_html(value)
        except (ParseError, ParserError, ValueError):
            # Error could occur because of invalid html document,
            # including '' values. ValueError raised by lxml when HTML
            # contains invalid attributes like empty '{}' from Django
            # template rendering. We don't want to return empty handed.
            partial_strip = value
        value = _strip_tags(partial_strip)
        return value.strip()  # clean cases we have <div>\n\n</div>
    return value
