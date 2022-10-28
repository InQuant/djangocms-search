# -*- coding: utf-8 -*-
import textwrap
from time import strftime
from datetime import datetime
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from rest_framework import serializers

from .index_base import get_page_document_class

import logging
logger = logging.getLogger('cms_search')


class CmsPageDocumentSerializer(DocumentSerializer):
    """Serializer for the Title document."""
    title = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    pub_date = serializers.SerializerMethodField()

    def get_title(self, hit):
        """ returns highligted title or title
        """
        title = hit.title
        highlights = self.get_highlights(hit)
        if (highlights.get('title')):
            title = highlights.get('title')[0]
        return title

    def get_text(self, hit):
        """ returns highligted text or text > 300 cutted at whitespace near 300
        """
        highlights = self.get_highlights(hit)
        if (highlights.get('text')):
            return highlights.get('text')[0]
        cuts = textwrap.wrap(hit.text, 300)
        return cuts[0] if cuts else hit.text

    def get_highlights(self, hit):
        if hasattr(hit.meta, 'highlight'):
            return hit.meta.highlight.__dict__['_d_']
        return {}

    def get_pub_date(self, obj):
        # TODO: FIXME - why is this a fucking string in obj type hit?
        dt = datetime.strptime(obj.pub_date[:26], '%Y-%m-%dT%H:%M:%S.%f')
        return strftime('%Y-%m-%d %H:%M:%S', dt.timetuple())

    class Meta(object):

        # Specify the correspondent document class
        document = get_page_document_class()

        # List the serializer fields. Note, that the order of the fields
        # is preserved in the ViewSet.
        fields = (
            'title',
            'slug',
            'text',
            'language',
            'pub_date',
            'login_required',
            'site_id',
            'url',
        )
