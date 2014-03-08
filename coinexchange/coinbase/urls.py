from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
    url(r'^authorize$', 'coinexchange.coinbase.views.authorize', name='coinbase_authorize'),
    url(r'^redirect_uri$', 'coinexchange.coinbase.views.redirect', name='coinbase_redirect'),
    url(r'^receive_payment_callback/(\d+)$', 'coinexchange.btc.pos.views.coinbase_recv_callback', name='coinbase_recv_callback'),

)
