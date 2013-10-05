from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'coinexchange.account.api.views.root'),
    url(r'^js', 'coinexchange.account.api.views.js'),
    url(r'^sell_bitcoin$', coinexchange.account.api.views.SellView.login_view(),
        name='api_sell'),
    url(r'^sell_bitcoin/(\d)$', coinexchange.account.api.views.SellView.login_view()),
    url(r'^withdraw$', coinexchange.account.api.views.WithdrawlView.login_view(),
        name='api_withdrawl'),
)
