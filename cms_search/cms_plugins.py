from django.utils.translation import gettext_lazy as _

from cms.plugin_pool import plugin_pool

from cmsplus.forms import PlusPluginFormBase, get_style_form_fields
from cmsplus.plugin_base import PlusPlugin, StylePluginMixin


# SearchResultList
# ----------------
#
class SearchResultListForm(PlusPluginFormBase):
    STYLE_CHOICES = 'SEARCH_RESULT_LIST_STYLES'
    plugin_title, extra_style, extra_css = get_style_form_fields(STYLE_CHOICES)


@plugin_pool.register_plugin
class SearchResultListPlugin(StylePluginMixin, PlusPlugin):
    name = _('Search Result')
    module = 'cms_search'
    allow_children = False
    form = SearchResultListForm
    render_template = 'cms_search/plugins/search-result.html'
    cache = False
