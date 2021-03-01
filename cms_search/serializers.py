# -*- coding: utf-8 -*-
from time import strftime
from datetime import datetime
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from rest_framework import serializers

from .index_register import DOCUMENT_CLASS as TitleDocument

import logging
logger = logging.getLogger('cms_search')


class TitleDocumentSerializer(DocumentSerializer):
    """Serializer for the Title document."""
    text = serializers.SerializerMethodField()
    pub_date = serializers.SerializerMethodField()

    def get_text(self, obj):
        return obj.text[:256]

    def get_pub_date(self, obj):
        # TODO: FIXME - why is this a fucking string in obj type hit?
        dt = datetime.strptime(obj.pub_date[:26], '%Y-%m-%dT%H:%M:%S.%f')
        return strftime('%Y-%m-%d %H:%M:%S', dt.timetuple())

    class Meta(object):

        # Specify the correspondent document class
        document = TitleDocument

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
