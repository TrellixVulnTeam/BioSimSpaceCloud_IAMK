
import datetime as _datetime

from Acquire.Crypto import PrivateKey as _PrivateKey

from Acquire.Service import call_function as _call_function
from Acquire.Service import Service as _Service

from Acquire.Accounting import Authorisation as _Authorisation
from Acquire.Accounting import Transaction as _Transaction
from Acquire.Accounting import create_decimal as _create_decimal

from ._errors import LoginError, AccountError

__all__ = ["Account", "get_accounts", "create_account"]


def _get_accounting_url():
    """Function to discover and return the default accounting url"""
    return "http://130.61.60.88:8080/r/accounting"


def _get_accounting_service(accounting_url=None):
    """Function to return the accounting service for the system"""
    if accounting_url is None:
        accounting_url = _get_accounting_url()

    privkey = _PrivateKey()
    response = _call_function(accounting_url, {}, response_key=privkey)

    try:
        service = _Service.from_data(response["service_info"])
    except:
        raise LoginError("Have not received the identity service info from "
                         "the identity service at '%s' - got '%s'" %
                         (accounting_url, response))

    if not service.is_accounting_service():
        raise LoginError(
            "You can only use a valid accounting service to get account info! "
            "The service at '%s' is a '%s'" %
            (accounting_url, service.service_type()))

    if service.service_url() != accounting_url:
        service.update_service_url(accounting_url)

    return service


def _get_account_uid(user, account_name, accounting_service=None,
                     accounting_url=None):
    """Return the UID of the account called 'account_name' that
        belongs to passed user on the passed accounting_service
    """
    if account_name is None:
        return None

    if accounting_service is None:
        accounting_service = _get_accounting_service(accounting_url)

    elif not accounting_service.is_accounting_service():
        raise ValueError("You can only query account using "
                         "a valid accounting service")

    args = {"user_uid": user.uid(),
            "account_name": str(account_name)}

    if user.is_logged_in():
        auth = _Authorisation(session_uid=user.session_uid(),
                              signing_key=user.signing_key())

        args["authorisation"] = auth.to_data()
        args["identity_url"] = user.identity_service().canonical_url()

    privkey = _PrivateKey()

    result = _call_function(
            "%s/get-account-uids" % accounting_service.service_url(),
            args=args,
            args_key=accounting_service.public_key(),
            response_key=privkey,
            public_cert=accounting_service.public_certificate())

    account_uids = result["account_uids"]

    for account_uid in account_uids:
        if account_uids[account_uid] == account_name:
            return account_uid

    raise AccountError("There is no account called '%s' for '%s'" %
                       (account_name, str(user)))


def _get_account_uids(user, accounting_service=None, accounting_url=None):
    """Return the names and UIDs of all of the accounts that belong
        to the passed user on the passed accounting_service
    """
    if accounting_service is None:
        accounting_service = _get_accounting_service(accounting_url)

    elif not accounting_service.is_accounting_service():
        raise ValueError("You can only query account using "
                         "a valid accounting service")

    if not user.is_logged_in():
        raise PermissionError(
            "You can only get information about about a user's accounts "
            "if they have authenticated their login")

    auth = _Authorisation(session_uid=user.session_uid(),
                          signing_key=user.signing_key())

    args = {"user_uid": user.uid(),
            "authorisation": auth.to_data(),
            "identity_url": user.identity_service().canonical_url()}

    privkey = _PrivateKey()

    result = _call_function(
            "%s/get-account-uids" % accounting_service.service_url(),
            args=args,
            args_key=accounting_service.public_key(),
            response_key=privkey,
            public_cert=accounting_service.public_certificate())

    return result["account_uids"]


def get_accounts(user, accounting_service=None, accounting_url=None):
    """Return all of the accounts of the passed user. Note that the
    user must be authenticated to call this function
    """
    if accounting_service is None:
        accounting_service = _get_accounting_service(accounting_url)

    account_uids = _get_account_uids(
                        user, accounting_service=accounting_service)

    accounts = []

    for uid in account_uids.keys():
        name = account_uids[uid]

        account = Account()
        account._account_name = name
        account._account_uid = uid
        account._user = user
        account._accounting_service = accounting_service

        accounts.append(account)

    return accounts


def create_account(user, account_name, description=None,
                   accounting_service=None, accounting_url=None):
    """Create an account on the accounting service for the passed
        user, calling the account 'account_name' and optionally
        passing in an account description. Note that the user must
        have authorised the login
    """
    if accounting_service is None:
        accounting_service = _get_accounting_service(accounting_url)

    elif not accounting_service.is_accounting_service():
        raise ValueError("You can only create an account by connecting "
                         "to a valid accounting service")

    if not user.is_logged_in():
        raise PermissionError(
            "You cannot create an account called '%s' for user "
            "'%s' as the user login has not been authenticated." %
            (account_name, user.name()))

    authorisation = _Authorisation(session_uid=user.session_uid(),
                                   signing_key=user.signing_key())

    args = {"user_uid": user.uid(),
            "account_name": str(account_name),
            "authorisation": authorisation.to_data(),
            "identity_url": user.identity_service().canonical_url()}

    if description is None:
        args["description"] = "Account '%s' for '%s'" % \
                                (str(account_name), user.name())
    else:
        args["description"] = str(description)

    privkey = _PrivateKey()

    result = _call_function(
                "%s/create-account" % accounting_service.service_url(),
                args,
                args_key=accounting_service.public_key(),
                response_key=privkey,
                public_cert=accounting_service.public_certificate())

    account_uid = result["account_uid"]

    account = Account()
    account._account_name = account_name
    account._account_uid = account_uid
    account._user = user
    account._accounting_service = accounting_service

    return account


class Account:
    """This is the client-side handle that is used to interact with
       an account on the service. If the account is created with a valid
       user login then you can perform tasks such as making payments,
       or issueing receipts or refunds. Otherwise, this is a simple
       interface that allows the account to be used as a receiver
       of value
    """
    def __init__(self, user=None, account_name=None, accounting_service=None,
                 accounting_url=None):
        """Construct the Account with the passed account_name, which is owned
           by the passed user. The account must already exist on the service,
           or else an exception will be raised
        """
        if user is not None:
            self._account_name = account_name
            self._user = user

            if accounting_service is None:
                accounting_service = _get_accounting_service(accounting_url)

            self._accounting_service = accounting_service

            self._account_uid = _get_account_uid(user, account_name,
                                                 accounting_service)
        else:
            self._account_uid = None

        self._last_update = None
        self._description = None

    def __str__(self):
        if self.is_null():
            return "Account::null"
        else:
            return "Account(name='%s', uid=%s)" % (self.name(), self.uid())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._account_uid == other._account_uid
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_null(self):
        """Return whether or not this is a null account"""
        return self._account_uid is None

    def uid(self):
        """Return the UID of this account"""
        return self._account_uid

    def name(self):
        """Return the name of this account"""
        if self.is_null():
            return None
        else:
            return self._account_name

    def owner(self):
        """Return the user who owns this account"""
        if self.is_null():
            return None
        else:
            return self._user

    def is_logged_in(self):
        """Return whether or not the user has an authenticated login
           to this account
        """
        try:
            return self._user.is_logged_in()
        except:
            return False

    def last_update_time(self):
        """Return the time of the last update of the balance"""
        return self._last_update

    def _refresh(self, force_update=False):
        """Refresh the current status of this account. This fetches
           the latest data, e.g. balance, limits etc. Note that this
           limits you to refreshing at most once every five seconds...
        """
        if self.is_null():
            self._overdraft_limit = _create_decimal(0)
            self._balance = _create_decimal(0)
            self._liability = _create_decimal(0)
            self._receivable = _create_decimal(0)
            self._spent_today = _create_decimal(0)
            return

        if force_update:
            should_refresh = True
        else:
            should_refresh = False

            if self._last_update is None:
                should_refresh = True
            else:
                should_refresh = (_datetime.datetime.now() -
                                  self._last_update).seconds > 5

        if not should_refresh:
            return

        if not self.is_logged_in():
            raise PermissionError(
                "You cannot get information about this account "
                "until after the owner has successfully authenticated.")

        auth = _Authorisation(session_uid=self._user.session_uid(),
                              signing_key=self._user.signing_key())

        args = {"user_uid": self._user.uid(),
                "identity_url": self._user.identity_service().canonical_url(),
                "authorisation": auth.to_data(),
                "account_name": self.name()}

        privkey = _PrivateKey()

        result = _call_function(
                    "%s/get-info" % self._accounting_service.service_url(),
                    args,
                    args_key=self._accounting_service.public_key(),
                    response_key=privkey,
                    public_cert=self._accounting_service.public_certificate())

        self._overdraft_limit = _create_decimal(result["overdraft_limit"])
        self._balance = _create_decimal(result["balance"])
        self._liability = _create_decimal(result["liability"])
        self._receivable = _create_decimal(result["receivable"])
        self._spent_today = _create_decimal(result["spent_today"])
        self._description = result["description"]

        self._last_update = _datetime.datetime.now()

    def description(self):
        """Return the description of this account"""
        if not self._description:
            self._refresh()

        return self._description

    def balance(self, force_update=False):
        """Return the current balance of this account"""
        self._refresh(force_update)
        return self._balance

    def liability(self, force_update=False):
        """Return the current total liability of this account"""
        self._refresh(force_update)
        return self._liability

    def receivable(self, force_update=False):
        """Return the current total accounts receivable of this account"""
        self._refresh(force_update)
        return self._receivable

    def spent_today(self, force_update=False):
        """Return the current amount spent today on this account"""
        self._refresh(force_update)
        return self._spent_today

    def overdraft_limit(self, force_update=False):
        """Return the overdraft limit of this account"""
        self._refresh(force_update)
        return self._overdraft_limit

    def is_beyond_overdraft_limit(self, force_update=False):
        """Return whether or not the current balance is beyond
           the overdraft limit
        """
        self._refresh(force_update)
        return (self._balance - self._liability) < -(self._overdraft_limit)

    def perform(self, transaction, account, is_provisional=False):
        """Tell this accounting service to apply the transfer described
           in 'transaction' from this account to the passed account. Note
           that the user must have logged into this account so that they
           have authorised this transaction. This returns the record
           of this transaction
        """
        if not self.is_logged_in():
            raise PermissionError("You cannot transfer value from '%s' to "
                                  "'%s' because you have not authenticated "
                                  "the user who owns this account" %
                                  (str(self), str(account)))

        if not isinstance(transaction, _Transaction):
            raise TypeError("The passed transaction must be of type "
                            "Transaction")

        if not isinstance(account, Account):
            raise TypeError("The passed credit account must be of type "
                            "Account")

        if transaction.is_null():
            return None

        auth = _Authorisation(session_uid=self._user.session_uid(),
                              signing_key=self._user.signing_key())

        if is_provisional:
            is_provisional = True
        else:
            is_provisional = False

        args = {"user_uid": self._user.uid(),
                "identity_url": self._user.identity_service().canonical_url(),
                "transaction": transaction.to_data(),
                "debit_account_uid": str(self.uid()),
                "credit_account_uid": str(account.uid()),
                "is_provisional": is_provisional,
                "authorisation": auth.to_data()}

        privkey = _PrivateKey()

        result = _call_function(
                    "%s/perform" % self._accounting_service.service_url(),
                    args,
                    args_key=self._accounting_service.public_key(),
                    response_key=privkey,
                    public_cert=self._accounting_service.public_certificate())

        return result["transaction_records"]

    def receipt(self, credit_note, receipted_value=None):
        """Receipt the passed credit note that contains a request to
           transfer value from another account to the passed account
        """
        if not self.is_logged_in():
            raise PermissionError("You cannot receipt a credit note as the "
                                  "user has not yet logged in!")

        if credit_note.account_uid() != self.uid():
            raise ValueError(
                "You cannot receipt a transaction from a different "
                "account! %s versus %s" % (credit_note.account_uid(),
                                           self.uid()))

        auth = _Authorisation(session_uid=self._user.session_uid(),
                              signing_key=self._user.signing_key())

        args = {"user_uid": self._user.uid(),
                "identity_url": self._user.identity_service().canonical_url(),
                "credit_note": credit_note.to_data(),
                "authorisation": auth.to_data()}

        if receipted_value is not None:
            args["receipted_value"] = str(_create_decimal(receipted_value))

        privkey = _PrivateKey()

        result = _call_function(
                    "%s/receipt" % self._accounting_service.service_url(),
                    args,
                    args_key=self._accounting_service.public_key(),
                    response_key=privkey,
                    public_cert=self._accounting_service.public_certificate())

        return result["transaction_record"]

    def refund(self, credit_note):
        """Refunds the passed credit note that contained a transfer of
           from another account to the passed account
        """
        if not self.is_logged_in():
            raise PermissionError("You cannot refund a credit note as the "
                                  "user has not yet logged in!")

        if credit_note.account_uid() != self.uid():
            raise ValueError(
                "You cannot refund a transaction from a different "
                "account! %s versus %s" % (credit_note.account_uid(),
                                           self.uid()))

        auth = _Authorisation(session_uid=self._user.session_uid(),
                              signing_key=self._user.signing_key())

        args = {"user_uid": self._user.uid(),
                "identity_url": self._user.identity_service().canonical_url(),
                "credit_note": credit_note.to_data(),
                "authorisation": auth.to_data()}

        privkey = _PrivateKey()

        result = _call_function(
                    "%s/refund" % self._accounting_service.service_url(),
                    args,
                    args_key=self._accounting_service.public_key(),
                    response_key=privkey,
                    public_cert=self._accounting_service.public_certificate())

        return result["transaction_record"]
