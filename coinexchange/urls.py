from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'coinexchange.views.home', name='home'),
    url(r'^$', 'coinexchange.public.views.home'),
    url(r'^login$', 'django.contrib.auth.views.login',
        {'template_name': 'coinexchange/login.html'}, name='auth_login'),
    url(r'^logout$', 'django.contrib.auth.views.logout',
        {'next_page': '/'}, name='auth_logout'),
    url(r'^signup$', 'coinexchange.account.views.signup', name='account_signup'),

    url(r'^account$', 'coinexchange.account.views.home', name='account_home'),
    url(r'^account/balance$', 'coinexchange.account.views.balance', name='account_balance'),
    url(r'^account/settings$', 'coinexchange.account.views.settings', name='account_settings'),
    url(r'^account/withdraw$', 'coinexchange.account.views.withdraw', name='account_withdrawl'),
    # Uncomment the next line to enable the admin:
    url(r'^djangoadmin/', include(admin.site.urls)),
)
