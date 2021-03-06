from django.conf.urls.defaults import include, patterns, url
from django.conf import settings
from django.contrib import admin

from funfactory.monkeypatches import patch
patch()

from cyder.cydns.api.v1.api import v1_dns_api
from cyder.core.cyuser import views as cyuser_views


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^$', include('cyder.core.system.urls')),
    (r'^system/', include('cyder.core.system.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^cydhcp/', include('cyder.cydhcp.urls')),
    (r'^cydns/', include('cyder.cydns.urls')),
    (r'^ctnr/', include('cyder.core.ctnr.urls')),
    #(r'^search/', include('cyder.core.search.urls')),
    (r'^user/', include('cyder.core.cyuser.urls')),
    (r'^api/', include(v1_dns_api.urls)),
    (r'^ctnr/', include('cyder.core.ctnr.urls')),
    (r'^search/', include('cyder.search.urls')),

    url(r'^accounts/login/$', 'django_cas.views.login', name='login'),
    url(r'^accounts/logout/$', 'django_cas.views.logout', name='logout'),
)

if settings.DEBUG:
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns(
        '',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )
