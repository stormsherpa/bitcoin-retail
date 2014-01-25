
from django.template import RequestContext

from coinexchange.btc import clientlib

class CoinExchangeContext(RequestContext):
    def __init__(self, request, context, *args, **kwargs):
        if request.user.is_authenticated():
            profile = request.user.get_profile()
#             balance = clientlib.get_user_balance(profile)
#             address = clientlib.get_user_address(profile)
            coinexchange_account = {'profile': profile,
#                                     'balance': balance,
#                                     'address': address,
                                    }
            print coinexchange_account
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
