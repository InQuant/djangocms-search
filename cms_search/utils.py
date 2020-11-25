# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib
import re

from django.db import models
from django.utils.encoding import force_text

import six
from lxml.etree import ParseError, ParserError
from lxml.html.clean import Cleaner as LxmlCleaner


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
    return re.sub(r'<[^>]*?>', ' ', force_text(value))


def strip_tags(value):
    """
    Returns the given HTML with all tags stripped.
    We use lxml to strip all js tags and then hand the result to django's
    strip tags. If value isn't valid, just return value since there is
    no tags to strip.
    """
    if isinstance(value, six.string_types):
        value = value.strip()

        try:
            partial_strip = LxmlCleaner().clean_html(value)
        except (ParseError, ParserError):
            # Error could occur because of invalid html document,
            # including '' values. We don't want to return empty handed.
            partial_strip = value
        value = _strip_tags(partial_strip)
        return value.strip()  # clean cases we have <div>\n\n</div>
    return value
