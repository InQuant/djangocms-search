from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from .views import TitleDocumentView

router = DefaultRouter()
titles = router.register(r'titles', TitleDocumentView, basename='titledocument')

urlpatterns = [
    url(r'^', include(router.urls)),
]
