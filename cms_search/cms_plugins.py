from django.utils.translation import gettext_lazy as _

from cms.plugin_pool import plugin_pool

from cmsplus.plugin_base import PlusPlugin


# SearchResultList
# ----------------
#
@plugin_pool.register_plugin
class SearchResultListPlugin(PlusPlugin):
    name = _('Search Result')
    module = 'cms_search'
    allow_children = False
    render_template = 'cms_search/plugins/search-result.html'
    cache = False
