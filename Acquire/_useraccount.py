

import base64 as _base64

from ._keys import PrivateKey as _PrivateKey
from ._otp import OTP as _OTP

__all__ = ["UserAccount"]

class UsernameError(Exception):
    pass

class ExistingAccountError(Exception):
    pass

class UserValidationError(Exception):
    pass

def _bytes_to_string(b):
    """Return the passed binary bytes safely encoded to
       a base64 utf-8 string"""
    return _base64.b64encode(b).decode("utf-8")

def _string_to_bytes(s):
    """Return the passed base64 utf-8 encoded binary data
       back converted from a string back to bytes"""
    return _base64.b64decode(s.encode("utf-8"))

class UserAccount:
    """This class holds all information about a user's account,
       e.g. their username, the sanitised username for the person
       on the system, their account keys, status etc.

       This data can be serialised to an from json to allow
       easy saving a retrieval from an object store
    """

    def __init__(self, username=None):
        """Construct from the passed username"""
        self._username = username
        self._sanitised_username = UserAccount.sanitise_username(username)
        self._privkey = None
        self._pubkey = None
        self._otp_secret = None

        if username is None:
            self._status = None
        else:
            self._status = "disabled"

    def __str__(self):
        return "UserAccount( name : %s )" % self._username

    def name(self):
        """Return the name of this account"""
        return self._username

    def username(self):
        """Synonym for 'name'"""
        return self.name()

    def sanitised_name(self):
        """Return the sanitised username"""
        return self._sanitised_username

    def max_open_sessions(self):
        """Return the maximum number of open login sessions
           (and open login requests) allowed for this user account"""
        return 10

    def login_request_timeout(self):
        """Return the number of hours a login request will
           remain active. This should normally be short, e.g. 30 minutes"""
        return 0.5

    def login_timeout(self):
        """Return the maximum number of hours a single login 
           can remain active. This should normally be of the order
           of 1-7 days, as individual calculations or workflows
           should not normally take longer than this"""
        return 7 * 24.0

    def login_root_url(self):
        """Return the root URL used to log into this account"""
        return "https://login.biosimspace.org/auth"

    def is_valid(self):
        """Return whether or not this is a valid account"""
        return not (self._status is None)

    def is_active(self):
        """Return whether or not this is an active account"""
        if self._status is None:
            return False
        else:
            return self._status == "active"

    def public_key(self):
        """Return the lines of the public key for this account"""
        return self._pubkey

    def	private_key(self):
       	"""Return the lines of the private key for this account"""
       	return self._privkey

    def status(self):
       	"""Return the status for this account"""
        if self._status is None:
            return "invalid"

       	return self._status

    def otp_secret(self):
        """Return the encrypted one-time-password secret"""
        return self._otp_secret

    def set_keys(self, privkey, pubkey, secret=None):
        """Set the private and public keys for this account. The 
           keys can be set from files or from a binary read file..
        """

        if self._status is None or privkey is None or pubkey is None:
            return

        try:
            privkey = open(privkey,"rb").read()
        except:
            pass

        try:
            pubkey = open(pubkey,"rb").read()
        except:
            pass

        self._privkey = privkey
        self._pubkey = pubkey
        self._otp_secret = secret

        self._status = "active"

    @staticmethod
    def sanitise_username(username):
        """This function returns a sanitised version of
           the username. This will ensure that the username
           is valid (must be between 3 and 50 characters) and
           will remove anything problematic for the object
           store
        """

        if username is None:
            return None

        if len(username) < 3 or len(username) > 50:
            raise UsernameError("The username must be between 3 and 50 characters!")

        return "_".join(username.split()).replace("/","") \
                  .replace("@","_AT_").replace(".","_DOT_")

    def validate_password(self, password, otpcode):
        """Validate that the passed password and one-time-code are valid.
           If they are, then do nothing. Otherwise raise an exception."""

        if not self.is_active():
            raise UserValidationError("Cannot validate against an inactive account")

        # see if we can decrypt the private key using the password
        privkey = _PrivateKey.read_bytes(self._privkey, password)

        # now decrypt the secret otp and validate the supplied otpcode
        otp = _OTP.decrypt(self._otp_secret, privkey)
        otp.verify(otpcode)

    def to_data(self):
        """Return a data representation of this object (dictionary)"""
        if self._username is None:
            return None

        data = {}
        data["username"] = self._username
        data["status"] = self._status

        # the keys and secret are arbitrary binary data.
        # These need to be base64 encoded and then turned into strings
        data["private_key"] = _bytes_to_string(self._privkey)
        data["public_key"] = _bytes_to_string(self._pubkey)
        data["otp_secret"] = _bytes_to_string(self._otp_secret)

        return data

    @staticmethod 
    def from_data(data):
        """Return a UserAccount constructed from the passed
           data (dictionary)
        """

        if data is None:
            return None

        user_account = UserAccount(data["username"])
        user_account._privkey = _string_to_bytes(data["private_key"])
        user_account._pubkey = _string_to_bytes(data["public_key"])
        user_account._status = data["status"]

        try:
            user_account._otp_secret = _string_to_bytes(data["otp_secret"])
        except:
            user_account._otp_secret = None

        return user_account
