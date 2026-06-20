# app_page/views.py

import logging
from django.views.generic import TemplateView


logger = logging.getLogger(__name__)


class HomePageView(TemplateView):
    template_name = 'base_hud.html'
