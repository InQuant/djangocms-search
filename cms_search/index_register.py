from .index_base import DefaultTitleDocument

import logging
logger = logging.getLogger('cms_search')

DOCUMENT_CLASS = DefaultTitleDocument


def register_custom_document(document_class):
    """Register the index document class"""
    logger.info(f'** register_custom_document: {document_class}')
    global DOCUMENT_CLASS
    DOCUMENT_CLASS = document_class
    return document_class
