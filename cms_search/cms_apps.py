from django.urls import path
from django.views.generic import TemplateView

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _


class CmsSearchApphook(CMSApp):
    app_name = "cms_search"
    name = _("CMS Search Application")

    def get_urls(self, page=None, language=None, **kwargs):
        return [
            path(r'^$', TemplateView.as_view(template_name='search-result.html')),
        ]


apphook_pool.register(CmsSearchApphook)  # register the application
