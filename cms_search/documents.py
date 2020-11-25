# -*- coding: utf-8 -*-
from time import strftime
from datetime import datetime

from django.db.models import Q
from django.dispatch import receiver

from cms.models import CMSPlugin, Title, Page
from cms.signals import post_publish, post_unpublish

from rest_framework import serializers

from elasticsearch_dsl import analyzer, analysis
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from .conf import settings
from .helpers import get_plugin_index_data, get_request
from .utils import clean_join

import logging
logger = logging.getLogger('cms_search')

''' ori:
html_strip = analyzer(
     'html_strip',
     tokenizer='standard',
     filter=['lowercase', 'stop', 'snowball'],
     char_filter=['html_strip']
 )
'''

de_snow_filter = analysis.token_filter('de_snow', type="snowball", language='German')
en_snow_filter = analysis.token_filter('en_snow', type="snowball", language='English')
de_stop_filter = analysis.token_filter('de_stop', type="stop", language='German')
en_stop_filter = analysis.token_filter('en_stop', type="stop", language='English')
de_ngram_filter = analysis.token_filter('de_ngram', type="ngram", min_gram=4, max_gram=5, language='German')
html_strip = analyzer(
    'html_strip',
    type='custom',
    tokenizer='standard',
    filter=['lowercase', de_snow_filter, en_snow_filter, de_stop_filter, en_stop_filter, de_ngram_filter],
    char_filter=['html_strip']
)


@registry.register_document
class TitleDocument(Document):

    text = fields.TextField(
        fielddata=True,
        analyzer=html_strip,
    )
    title = fields.TextField(
        fielddata=True,
        analyzer=html_strip,
        fields={
            'raw': fields.KeywordField(),
        }
    )
    slug = fields.TextField(
        fielddata=True,
        fields={
            'raw': fields.KeywordField(),
        }
    )

    pub_date = fields.DateField(store=True, index=False)
    login_required = fields.BooleanField()
    site_id = fields.IntegerField(store=True, index=True)
    url = fields.TextField(
        store=True,
        index=False,
    )

    class Index:
        # Name of the Elasticsearch index
        name = 'cmspages'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Title  # The model associated with this Document

        # The fields of the model you want to be indexed in Elasticsearch
        fields = [
            'id',
            'language',
        ]

        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True

    def prepare_text(self, obj):
        logger.debug('*** index prepare text: %s' % obj)
        current_page = obj.page
        placeholders = self.get_page_placeholders(current_page)
        plugins = self.get_plugin_queryset(obj.language).filter(placeholder__in=placeholders)
        request = self.get_request_instance(obj)

        text_tokens = [self.prepare_title(obj)]
        for base_plugin in plugins:
            plugin_text_content = self.get_plugin_search_text(base_plugin, request)
            text_tokens.append(plugin_text_content)

        page_meta_description = current_page.get_meta_description(fallback=False)

        if page_meta_description:
            text_tokens.append(page_meta_description)

        page_meta_keywords = getattr(current_page, 'get_meta_keywords', None)
        if callable(page_meta_keywords):
            text_tokens.append(page_meta_keywords())

        logger.debug(str(text_tokens))
        return clean_join(' ', text_tokens)

    def get_request_instance(self, obj):
        return get_request(obj.language)

    def prepare_pub_date(self, obj):
        return obj.page.publication_date

    def prepare_login_required(self, obj):
        return obj.page.login_required

    def prepare_site_id(self, obj):
        return obj.page.node.site_id

    def prepare_url(self, obj):
        return obj.page.get_absolute_url(language=obj.language)

    def prepare_title(self, obj):
        return obj.title

    def prepare_description(self, obj):
        return obj.meta_description or None

    def get_plugin_queryset(self, language):
        queryset = CMSPlugin.objects.filter(language=language)
        return queryset

    def get_page_placeholders(self, page):
        """
        In the project settings set up the variable

        PLACEHOLDERS_SEARCH_LIST = {
            # '*' is mandatory if you define at least one slot rule
            '*': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            }
            'reverse_id_alpha': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            'reverse_id_beta': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            'reverse_id_only_include': {
                'include': [ 'slot1', 'slot2', etc. ],
            },
            'reverse_id_only_exclude': {
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            # exclude it from the placehoders search list
            # (however better to remove at all to exclude it)
            'reverse_id_empty': []
            etc.
        }

        or leave it empty

        PLACEHOLDERS_SEARCH_LIST = {}
        """
        reverse_id = page.reverse_id
        args = []
        kwargs = {}

        placeholders_by_page = getattr(settings, 'PLACEHOLDERS_SEARCH_LIST', {})

        if placeholders_by_page:
            filter_target = None
            excluded = []
            slots = []
            if '*' in placeholders_by_page:
                filter_target = '*'
            if reverse_id and reverse_id in placeholders_by_page:
                filter_target = reverse_id
            if not filter_target:
                raise AttributeError('Leave PLACEHOLDERS_SEARCH_LIST empty or set up at least the generic handling')
            if 'include' in placeholders_by_page[filter_target]:
                slots = placeholders_by_page[filter_target]['include']
            if 'exclude' in placeholders_by_page[filter_target]:
                excluded = placeholders_by_page[filter_target]['exclude']
            diff = set(slots) - set(excluded)
            if diff:
                kwargs['slot__in'] = diff
            else:
                args.append(~Q(slot__in=excluded))
        return page.placeholders.filter(*args, **kwargs)

    def get_plugin_search_text(self, base_plugin, request):
        plugin_content_bits = get_plugin_index_data(base_plugin, request)
        return clean_join(' ', plugin_content_bits)

    def get_model(self):
        return Title

    def get_queryset(self):
        """
        Return the queryset that should be indexed by this doc type.
        """
        return Title.objects.public()

    def update(self, thing, refresh=None, action='index', parallel=False, **kwargs):
        logger.info('** about to update index: %s, %s' % (action, thing))
        return super().update(thing, refresh, action, parallel, **kwargs)


@receiver(post_publish, sender=Page)
def on_page_post_publish(sender, **kwargs):
    try:
        page = kwargs['instance']
        logger.info('** on_post_publish %s' % str(page))
        TitleDocument().update(page.get_title_obj(), refresh=True, action='index')
    except Exception as e:
        logger.error('** index update failed for page: %s, %s' % (str(page), str(e)))
        logger.error('on_page_post_publish Error - Elasticsearch running?')
        logger.exception(e)


@receiver(post_unpublish, sender=Page)
def on_title_post_unpublish(sender, **kwargs):
    try:
        page = kwargs['instance']
        logger.info('** on_post_unpublish %s' % str(page))
        TitleDocument().update(page.get_title_obj(), refresh=True, action='delete')
    except Exception as e:
        logger.error('** index removal failed for page: %s, %s' % (str(page), str(e)))
        logger.error('on_title_post_unpublish Error - Elasticsearch running?')
        logger.exception(e)


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
