from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'coinexchange.account.api.views.root'),
    url(r'^state$', 'coinexchange.account.api.views.state'),
    url(r'^js$', 'coinexchange.account.api.views.js'),
    url(r'^xmpp$', 'coinexchange.account.api.views.xmpp_creds'),
    url(r'^newsale$', 'coinexchange.account.api.views.newsale'),
    url(r'^sale$', 'coinexchange.account.api.views.sale_list'),
    url(r'^sale/(\d+)$', 'coinexchange.account.api.views.sale'),
    url(r'^withdraw$', coinexchange.account.api.views.WithdrawlView.login_view(),
        name='api_withdrawl'),
)
