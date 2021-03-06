from django.conf.urls import patterns, include, url

import coinexchange.account.api.views

urlpatterns = patterns('',
#     url(r'^$', 'coinexchange.btc.pos.views.admin', name='pos_admin'),
    url(r'^merchant_settings$', 'coinexchange.btc.pos.views.merchant_settings', name='pos_merchant_settings'),
    url(r'^batch/(\d+)$', 'coinexchange.btc.pos.views.batch', name='pos_batch'),
    url(r'^make_batch$', 'coinexchange.btc.pos.views.make_batch', name='pos_make_batch'),
    url(r'^coinbase_txid/(.+)$', 'coinexchange.btc.pos.views.coinbase_tx_detail', name='pos_tx_detail'),
    url(r'^generate_batch_report', 'coinexchange.btc.pos.views.generate_batch_report', name='pos_batch_report'),
    url(r'^print_last_report', 'coinexchange.btc.pos.views.print_last_batch_report', name='pos_print_batch_report'),
)
