# app_page/templatetags/custom_tags.py

from django import template
register = template.Library()

@register.inclusion_tag('icons/_icon_wrapper.html')
def icon(name, size='md'):
    return {'icon_name': name, 'size': size}