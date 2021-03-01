from django_elasticsearch_dsl_drf.constants import (
    LOOKUP_FILTER_RANGE,
    LOOKUP_QUERY_IN,
)
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    IdsFilterBackend,
    OrderingFilterBackend,
    DefaultOrderingFilterBackend,
    SearchFilterBackend,
)
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from django_elasticsearch_dsl_drf.pagination import PageNumberPagination

from .index_register import DOCUMENT_CLASS as TitleDocument
from .serializers import TitleDocumentSerializer


class TitleDocumentView(BaseDocumentViewSet):

    document = TitleDocument
    serializer_class = TitleDocumentSerializer
    pagination_class = PageNumberPagination
    lookup_field = 'id'
    filter_backends = [
        FilteringFilterBackend,
        IdsFilterBackend,
        OrderingFilterBackend,
        DefaultOrderingFilterBackend,
        SearchFilterBackend,
    ]
    # Define search fields
    search_fields = {
        'title': {'boost': 4},
        'text': None,
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
        'title': 'title',
        'pub_date': 'pub_date',
    }
    # Specify default ordering
    ordering = ('_score', 'title', 'pub_date',)
