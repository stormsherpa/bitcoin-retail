

from django.template import RequestContext, Context, loader

from coinexchange.btc import clientlib
from coinexchange import coinbase

def warn_missing_coinbase_api(request):
    if request.user.is_authenticated():
        profile = request.user.get_profile()
        try:
            api = coinbase.get_api_instance(profile)
            coinbase.get_account_info(api)
        except Exception as e:
            print "%s: %s" % (e.__class__, e)
            api = None
        if not api:
            t = loader.get_template("coinexchange/account/link_to_coinbase_error.html")
            c = Context({})
            msg = t.render(c)
            if not msg in StatusMessages(request).list_warnings():
                StatusMessages.add_warning(request, msg)
#             setattr(request, 'missing_coinbase_api', True)
            return True
    return False

class CoinExchangeContext(RequestContext):
    def __init__(self, request, context, *args, **kwargs):
        if request.user.is_authenticated():
            profile = request.user.get_profile()
            api_warned = warn_missing_coinbase_api(request)
            print "API Missing: %s" % api_warned
#             balance = clientlib.get_user_balance(profile)
#             address = clientlib.get_user_address(profile)
            coinexchange_account = {'profile': profile,
                                    'coinbase_unavailable': api_warned,
#                                     'balance': balance,
#                                     'address': address,
                                    }
            print "Coinexchange account: %s" % coinexchange_account
            context['coinexchange_account'] = coinexchange_account
        else:
            context['coinexchange_account'] = dict()
        context['status_messages'] = StatusMessages(request)
        RequestContext.__init__(self, request, context, *args, **kwargs)

class StatusMessages():
    def __init__(self, request):
        if not request.session.get('errors', False):
            request.session['errors'] = list()
        if not request.session.get('warnings', False):
            request.session['warnings'] = list()
        if not request.session.get('success', False):
            request.session['success'] = list()
        self.request = request

    def all_messages(self):
        result = list()
        for m in self.request.session.get('errors', list()):
            result.append( ('error', m) )
        for m in self.request.session.get('warnings', list()):
            result.append( ('warning', m) )
        for m in self.request.session.get('success', list()):
            result.append( ('success', m) )
        return result

    @staticmethod
    def add_error(request, err):
        if not request.session.get('errors', False):
            request.session['errors'] = list()
        request.session['errors'].append(err)
        
    def list_errors(self):
        return self.request.session['errors']

    def consume_errors(self):
        errors = self.request.session['errors']
        self.request.session['errors'] = list()
        return errors

    @staticmethod
    def add_warning(request, err):
        if not request.session.get('warnings', False):
            request.session['warnings'] = list()
        request.session['warnings'].append(err)
        
    def list_warnings(self):
        return self.request.session['warnings']

    def consume_warnings(self):
        warnings = self.request.session['warnings']
        self.request.session['warnings'] = list()
        return warnings

    @staticmethod
    def add_success(request, err):
        if not request.session.get('success', False):
            request.session['success'] = list()
        request.session['success'].append(err)
        
    def list_success(self):
        return self.request.session['success']

    def consume_success(self):
        success = self.request.session['success']
        self.request.session['success'] = list()
        return success
