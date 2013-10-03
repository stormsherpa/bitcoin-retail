from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^paypal$', 'coinexchange.paymentmethod.views.Paypal', name='payment_paypal')
)
