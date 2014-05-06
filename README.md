Bitcoin Retail
===================

Bitcoin Retail was my entry for bithack.  This code base has been my playground for working with bitcoin in
various ways.  There is code in this project for doing more than bitcoin point of sale and examples of different
way of working with bitcoin can be seen.

To use this there are some dependencies.

* RabbitMQ - Move post processing out of web request process context
* Fork21 - https://github.com/skruger/ejabberd (requires special api module for sending messages to point of sale UI)
* bitcoind - If reenabled this project is capable of working directly with bitcoind
* coinbase oauth credentials

This project is in a state that was specifically deployable for bithack.  After some cleanup I hope to share my
deployment automation to ease setup for anyone who is interested.

