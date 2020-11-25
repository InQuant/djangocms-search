# -*- coding: utf-8 -*-
from django.conf import settings  # noqa: F401
from appconf import AppConf


class CmsSearchAppConf(AppConf):

    EXCLUDED_PLUGINS = []

    class Meta:
        prefix = 'CMS_SEARCH'
