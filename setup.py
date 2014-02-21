#!/usr/bin/env python

from setuptools import setup
from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt')

packages = [
    'coinexchange',
    'coinexchange.account',
    'coinexchange.account.api',
    'coinexchange.btc',
    'coinexchange.btc.pos',
    'coinexchange.btc.pos.management',
    'coinexchange.btc.pos.management.commands',
    'coinexchange.btc.queue',
    'coinexchange.main',
    'coinexchange.main.management',
    'coinexchange.main.management.commands',
    'coinexchange.public',
    ]

setup(name="coinexchange",
      version="0.1",
      description="Coinexchange web application",
      author="Storm Sherpa",
      author_email="skruger@fastinfra.com",
      include_package_data=True,
      packages=packages,
      scripts=['scripts/coinexchange-manage.py'],
      install_requires=[str(ir.req) for ir in install_reqs])

