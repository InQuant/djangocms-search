# -*- coding: utf-8 -*-
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from cms.models import CMSPlugin, PageContent, Page

from elasticsearch_dsl import analyzer, analysis

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .conf import settings
from .helpers import get_plugin_index_data, get_request
from .utils import clean_join

import logging
import time
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
    # filter=['lowercase', de_decompounder, 'german_normalization', de_stop, en_stop, de_snow, en_snow, de_stemmer, en_stemmer],
    filter=['lowercase', de_decompounder, 'german_normalization', de_stop, en_stop, de_stemmer, en_stemmer],
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
        analyzer=html_strip,
        fields={
            'raw': fields.KeywordField(),
        }
    )

    text = fields.TextField(
        analyzer=html_strip,
    )

    item_type = fields.TextField(
        analyzer=html_strip,
        fields={
            'raw': fields.KeywordField(),
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
        analyzer=html_strip,
        fields={
            'raw': fields.KeywordField(),
        }
    )
    slug = fields.TextField(
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

    def prepare_text(self, pc:PageContent):
        logger.debug('*** index prepare text: %s' % pc)
        current_page = pc.page

        placeholders = pc.placeholders.all()
        plugins = self.get_plugin_queryset(pc.language).filter(placeholder__in=placeholders)
        request = self.get_request_instance(pc)

        text_tokens = [self.prepare_description(pc)]
        for base_plugin in plugins:
            if self.is_plugin_indexable(base_plugin):
                try:
                    plugin_text_content = self.get_plugin_search_text(base_plugin, request)
                    text_tokens.append(plugin_text_content)
                except Exception as e:
                    logger.error(
                        f'Cannot render plugin ({base_plugin}, {base_plugin.id}) for index: {e}')
                    continue

        title = self.prepare_title(pc)
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
        return obj.versions.filter(state='published').last().modified

    def prepare_site_id(self, obj):
        return obj.page.node.site_id

    def prepare_url(self, obj):
        return obj.page.get_absolute_url(language=obj.language)

    def prepare_title(self, obj):
        return obj.title or obj.page.get_title() or ''

    def prepare_description(self, obj):
        return obj.page.get_meta_description(fallback=False) or ''

    def get_plugin_queryset(self, language):
        queryset = CMSPlugin.objects.filter(language=language)
        return queryset

    def get_plugin_search_text(self, base_plugin, request):
        plugin_content_bits = get_plugin_index_data(base_plugin, request)
        return clean_join(' ', plugin_content_bits)

    def get_model(self):
        return PageContent

    def get_queryset(self):
        """
        Return the queryset that should be indexed by this doc type.
        Batch-loads all pages to avoid N+1 queries on parent_page traversal.
        """
        pages = list(Page.objects.only('id', 'login_required', 'parent'))
        page_map = {p.id: p for p in pages}

        def _is_login_required(page_id):
            page = page_map.get(page_id)
            if not page:
                return False
            if page.login_required:
                return True
            if page.parent_id:
                return _is_login_required(page.parent_id)
            return False

        indexable_ids = [p.id for p in pages if not _is_login_required(p.id)]
        return PageContent.objects.filter(page__id__in=indexable_ids)


def page_login_required(page, recursive=False):
    if page.login_required:
        return True
    if recursive and page.parent_page:
        return page_login_required(page.parent_page, recursive)
    return False


def _index_op_with_retry(operation, max_retries=2):
    """Execute an ES index operation with retry and exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            operation()
            return
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f'ES index operation failed (attempt {attempt + 1}), retrying in {wait}s: {e}')
                time.sleep(wait)
            else:
                raise


def update_index_for_page_content(page_document_cls, page_content:PageContent):
    try:
        page = page_content.page
        if page_login_required(page, recursive=True):
            return
        logger.info(f'** update_index_for_page_instance {page} ({page_content})')
        _index_op_with_retry(
            lambda: page_document_cls().update(page_content, refresh=True, action='index')
        )
    except Exception as e:
        logger.error(f'** index update failed for page: {page} ({page_content}), {e}')
        logger.error('on_page_post_publish Error - Elasticsearch running?')
        logger.exception(e)


def remove_index_for_page_instance(page_document_cls, page_content:PageContent):
    try:
        page = page_content.page
        logger.info(f'** remove_index_for_page_instance {page}, ({page_content})')
        _index_op_with_retry(
            lambda: page_document_cls().update(page_content, refresh=True, action='delete')
        )
    except Exception as e:
        logger.error(f'** index removal failed for page: {page}, ({page_content})')
        logger.error('on_title_post_unpublish Error - Elasticsearch running?')
        logger.exception(e)


def custom_page_document_register(page_document_class):
    global PAGE_DOCUMENT_CLS
    PAGE_DOCUMENT_CLS = page_document_class
    registry.register_document(page_document_class)

def get_page_document_class():
    return PAGE_DOCUMENT_CLS