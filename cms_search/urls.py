from django.urls import re_path, include
from rest_framework.routers import DefaultRouter

from .views import TitleDocumentView

router = DefaultRouter()
titles = router.register(r'titles', TitleDocumentView, basename='titledocument')

urlpatterns = [
    re_path(r'^', include(router.urls)),
]
