# app_page/views.py


from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = 'base_hud.html'
