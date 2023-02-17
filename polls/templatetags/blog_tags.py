from django import template
register = template.Library()
from ..models import Post
from django.utils.safestring import mark_safe
import markdown


@register.simple_tag
def total_posts():
    return Post.objects.all().count()


@register.inclusion_tag('post/latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.objects.all().order_by('-publish')[:count]
    return {'latest_posts': latest_posts}


@register.filter(name='markdown')
def markdown_format(text):
    return mark_safe(markdown.markdown(text))