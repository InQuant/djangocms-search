# -*- coding: utf-8 -*-
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from cms.models import CMSPlugin, PageContent, Page

from elasticsearch_dsl import analyzer, analysis

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl_drf.compat import StringField
from django_elasticsearch_dsl.registries import registry

from .conf import settings
from .helpers import get_plugin_index_data, get_request
from .utils import clean_join

import logging
logger = logging.getLogger('cms_search')

PAGE_DOCUMENT_CLS = None # to be set trough custom_page_document_register

''' ori:
html_strip = analyzer(
     'html_strip',
     tokenizer='standard',
     filter=['lowercase', 'stop', 'snowball'],
     char_filter=['html_strip']
 )
'''

en_snow = analysis.token_filter('en_snow', type="snowball", language='English')
en_stop = analysis.token_filter('en_stop', type="stop", language='English')
en_stemmer = analysis.token_filter('en_stemmer', type="stemmer", language='English')
de_snow = analysis.token_filter('de_snow', type="snowball", language='German')
de_stop = analysis.token_filter('de_stop', type="stop", language='German')
en_ngram = analysis.token_filter('en_ngram', type="ngram", min_gram=5, max_gram=5, language='English')
de_ngram = analysis.token_filter('de_ngram', type="ngram", min_gram=5, max_gram=5, language='German')
de_stemmer = analysis.token_filter('de_stemmer', type="stemmer", language='German')
de_decompounder = analysis.token_filter('de_decompounder', type="hyphenation_decompounder",
    word_list_path="analysis/dictionary-de.txt", hyphenation_patterns_path="analysis/de_DR.xml",
    only_longest_match=True, min_subword_size=3)

# best so far for german seems to be a 3/3 ngram tokenizer with the configured filters.
# Seems to be the best balance between good matches and to many hits
html_strip = analyzer(
    'html_strip',
    type='custom',
    # tokenizer=analysis.tokenizer('ngram', type='ngram', min_gram=3, max_gram=3),
    tokenizer='standard',
    # filter=['lowercase', en_snow, en_stop, de_snow, de_stop, 'german_normalization', de_stemmer],
    filter=['lowercase', de_decompounder, 'german_normalization', de_stop, en_stop, de_snow,
       en_snow, de_stemmer, en_stemmer],
    char_filter=['html_strip']
)
class TitleDocumentBase(Document):
    """
    Use e.g. with an Book Model:
    from django_elasticsearch_dsl.registries import registry

    @registry.register_document
    BookDocument(DocumentBase):

        class Django:
            model = Book  # The model associated with this Document

            # The fields of the model you want to be indexed in Elasticsearch
            fields = [
                'id',
                'language',
            ]

            # Ignore auto updating of Elasticsearch when a model is saved
            # or deleted:
            ignore_signals = True  # see update below
    """
    title = fields.TextField(
        fielddata=True,
        analyzer=html_strip,
        fields={
            'raw': fields.KeywordField(),
        }
    )

    text = fields.TextField(
        fielddata=True,
        analyzer=html_strip,
    )

    item_type = StringField(
        analyzer=html_strip,
        fields={
            'raw': StringField(analyzer='keyword'),
        }
    )

    class Index:
        # Name of the Elasticsearch index
        name = 'titlemodels'  # set index name
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    def prepare_title(self, obj):
        return getattr(obj, 'name', '')

    def prepare_text(self, obj):
        return getattr(obj, 'content', '')

    def prepare_item_type(self, obj):
        return obj.__class__.__name__.lower()

    def prepare_content_type_id(self, obj):
        return ContentType.objects.get_for_model(obj).id

    def get_model(self):
        raise NotImplementedError('get_model must be implemented in document class.')

    def update(self, thing, refresh=None, action='index', parallel=False, **kwargs):
        logger.info('** about to update index: %s, %s' % (action, thing))
        return super().update(thing, refresh, action, parallel, **kwargs)


class CmsPageDocumentBase(TitleDocumentBase):

    description = fields.TextField(
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
        model = PageContent  # The model associated with this Document

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

        text_tokens = [self.prepare_description(obj)]
        for base_plugin in plugins:
            if self.is_plugin_indexable(base_plugin):
                try:
                    plugin_text_content = self.get_plugin_search_text(base_plugin, request)
                    text_tokens.append(plugin_text_content)
                except Exception as e:
                    logger.error(
                        f'Cannot render plugin ({base_plugin}, {base_plugin.id}) for index: {e}')
                    continue

        title = self.prepare_title(obj)
        if title:
            text_tokens.append(title)

        page_meta_keywords = getattr(current_page, 'get_meta_keywords', None)
        if callable(page_meta_keywords):
            text_tokens.append(page_meta_keywords())

        logger.debug(str(text_tokens))
        return clean_join(' ', text_tokens)

    def is_page_indexable(self, page):
        """ called before a page will be indexed.
            if one returns False plugin will be skipped.
        """
        return True

    def is_plugin_indexable(self, plugin):
        """ called before a plugin will be indexed.
            if one returns False plugin will be skipped.
        """
        return True

    def get_request_instance(self, obj):
        return get_request(obj.language)

    def prepare_pub_date(self, obj):
        return obj.page.publication_date

    def prepare_site_id(self, obj):
        return obj.page.node.site_id

    def prepare_url(self, obj):
        return obj.page.get_absolute_url(language=obj.language)

    def prepare_title(self, obj):
        return obj.page.get_page_title() or obj.page.get_title() or ''

    def prepare_description(self, obj):
        return obj.page.get_meta_description(fallback=False) or ''

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
        return PageContent

    def get_queryset(self):
        """
        Return the queryset that should be indexed by this doc type.
        """
        indexable_pages = []
        for page in Page.objects.public().filter(login_required=False):
            if not page_login_required(page, recursive=True):
                indexable_pages.append(page.id)
        return PageContent.objects.filter(page__id__in=indexable_pages)


def page_login_required(page, recursive=False):
    if page.login_required:
        return True
    if recursive and page.parent_page:
        return page_login_required(page.parent_page, recursive)
    return False


def update_index_for_page_instance(page_document_cls, instance, language):
    try:
        page = instance.get_public_object()
        if page_login_required(page, recursive=True):
            return
        logger.info('** update_index_for_page_instance %s' % str(page))
        title = page.title_set.get(language=language)
        page_document_cls().update(title, refresh=True, action='index')
    except Exception as e:
        logger.error('** index update failed for page: %s, %s' % (str(page), str(e)))
        logger.error('on_page_post_publish Error - Elasticsearch running?')
        logger.exception(e)


def remove_index_for_page_instance(page_document_cls, instance, language):
    try:
        page = instance.get_public_object()
        logger.info('** remove_index_for_page_instance %s' % str(page))
        title = page.title_set.get(language=language)
        page_document_cls().update(title, refresh=True, action='delete')
    except Exception as e:
        logger.error('** index removal failed for page: %s, %s' % (str(page), str(e)))
        logger.error('on_title_post_unpublish Error - Elasticsearch running?')
        logger.exception(e)


def custom_page_document_register(page_document_class):
    global PAGE_DOCUMENT_CLS
    PAGE_DOCUMENT_CLS = page_document_class
    registry.register_document(page_document_class)

def get_page_document_class():
    return PAGE_DOCUMENT_CLS