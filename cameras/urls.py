"""
Camera API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CameraViewSet, CameraSettingsViewSet

router = DefaultRouter()
router.register(r'cameras', CameraViewSet, basename='camera')
router.register(r'settings', CameraSettingsViewSet, basename='settings')

urlpatterns = router.urls
