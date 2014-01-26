from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
    url(r'^$', 'coinexchange.btc.pos.views.main', name='pos_home'),
)
