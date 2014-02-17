from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
    url(r'^$', 'coinexchange.btc.pos.views.admin', name='pos_admin'),
    url(r'^make_batch$', 'coinexchange.btc.pos.views.make_batch', name='pos_make_batch'),
)