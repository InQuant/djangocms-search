from elasticsearch_dsl import TermsFacet
from django_elasticsearch_dsl_drf.constants import (
    LOOKUP_FILTER_RANGE,
    LOOKUP_QUERY_IN,
)
from django_elasticsearch_dsl_drf.filter_backends import (
    DefaultOrderingFilterBackend,
    FilteringFilterBackend,
    IdsFilterBackend,
    FacetedSearchFilterBackend,
    CompoundSearchFilterBackend,
    OrderingFilterBackend,
    MultiMatchSearchFilterBackend,
    HighlightBackend,
    SearchFilterBackend,
)
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from django_elasticsearch_dsl_drf.pagination import PageNumberPagination

from .index_base import get_page_document_class
from .serializers import CmsPageDocumentSerializer

class TitleDocumentView(BaseDocumentViewSet):

    document = get_page_document_class()
    serializer_class = CmsPageDocumentSerializer
    pagination_class = PageNumberPagination
    lookup_field = 'id'
    filter_backends = [
        DefaultOrderingFilterBackend,
        FilteringFilterBackend,
        IdsFilterBackend,
        FacetedSearchFilterBackend,
        CompoundSearchFilterBackend,
        OrderingFilterBackend,
        MultiMatchSearchFilterBackend,
        HighlightBackend,
        SearchFilterBackend,
    ]
    # Define search fields
    search_fields = {
        'title': {'boost': 4},
        'text': None,
    }

    faceted_search_fields = {
        'item_type': {
            'field': 'item_type.raw',
            'facet': TermsFacet,
            'enabled': True
        },
    }

    multi_match_search_fields = {
        'title': {'boost': 4},
        'text': None,
    }

    multi_match_options = {
        'type': 'phrase'
    }

    # Define highlight fields
    highlight_fields = {
        'title': {
            'enabled': True,
            'options': {
                'pre_tags': ["<mark>"],
                'post_tags': ["</mark>"],
            }
        },
        'text': {
            'enabled': True,
            'options': {
                'fragment_size': 100,
                'number_of_fragments': 3,
                'pre_tags': ["<mark>"],
                'post_tags': ["</mark>"],
            }
        },
    }

    # Define filter fields
    filter_fields = {
        'id': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
            ],
        },
        'slug': 'slug.raw',
        'title': 'title.raw',
        'pub_date': 'pub_date',
    }

    # Define ordering fields
    ordering_fields = {
        '_score': '_score',
        'title': 'title.raw',
        'pub_date': 'pub_date',
    }

    # Specify default ordering (_score is descending by default in ES)
    ordering = ('_score', 'pub_date', 'title.raw')
