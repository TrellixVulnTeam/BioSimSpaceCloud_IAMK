"""
This script writes the login information (pem key etc.) that is needed
by the identity service to log onto the object store as the
identity admin user account
"""

import json
import sys
import os

from Acquire.Crypto import PrivateKey

## First create the login info to connect to the account

"""
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaalwrmdvqwargpp3ik3gybyc2pjc6duzivk6wctghvpwnnth6adc5a
fingerprint=0f:01:62:1b:82:a9:97:06:f7:66:dd:2a:3d:82:63:34
key_file=~/.oci/oci_api_key.pem
pass_phrase=XXXXXX
tenancy=ocid1.tenancy.oc1..aaaaaaaa3eiex6fbfj626uwhs3dg24oygknrhhgfj4khqearluf4i74zdt2a
region=eu-frankfurt-1
"""

data = {}

# OCID for the user "bss-auth-service"
data["user"] = "ocid1.user.oc1..aaaaaaaalwrmdvqwargpp3ik3gybyc2pjc6duzivk6wctghvpwnnth6adc5a"

# Fingerprint for the login keyfile
data["fingerprint"] = "1d:75:2d:85:06:ed:e3:7e:52:56:a2:5e:7e:d6:c6:3f"

# The keyfile itself - we will now read the file and pull it into text
keyfile = sys.argv[1]
data["key_lines"] = open(sys.argv[1],"r").readlines()

# The tenancy in which this user and everything exists!
data["tenancy"] = "ocid1.tenancy.oc1..aaaaaaaa3eiex6fbfj626uwhs3dg24oygknrhhgfj4khqearluf4i74zdt2a"

# The passphrase to unlock the key - VERY SECRET!!!
data["pass_phrase"] = sys.argv[2]

# Make sure that this is the correct password...
privkey = PrivateKey.read(sys.argv[1],sys.argv[2])

# The region for this tenancy
data["region"] = "eu-frankfurt-1"

print(json.dumps(data))

os.system("fn config app identity LOGIN_JSON '%s'" % json.dumps(data))

## Now create the bucket info so we know where the bucket is
## that will store all data related to logging into accounts

data = {}
data["compartment"] = "ocid1.compartment.oc1..aaaaaaaat33j7w74mdyjenwoinyeawztxe7ri6qkfbm5oihqb5zteamvbpzq"
data["bucket"] = "acquire_identity"

print(json.dumps(data))

os.system("fn config app identity BUCKET_JSON '%s'" % json.dumps(data))
os.system("fn config app identity SERVICE_PASSWORD '%s'" % sys.argv[2])
