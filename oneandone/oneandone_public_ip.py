#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: oneandone_public_ip
short_description: Configure 1&1 public IPs.
description:
     - List, create, update, remove private networks
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  reverse_dns:
    description:
      - Reverse DNS name.
    required: false
    type: 'string'
    maxLength: 256
  datacenter:
    description:
      - ID of the datacenter where the IP will be created (only for unassigned IPs).
    type: 'string'
    required: false
  type:
    description:
      - Type of IP. Currently, only IPV4 is available.
    type: 'string'
    choices: ["IPV4", "IPV6"]
    default: 'IPV4'
    required: false

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (amel@stackpointcloud.com)
'''

EXAMPLES = '''

# Create a public IPs.

- oneandone_public_ip:
    auth_token: oneandone_private_api_key
    reverse_dns: example.com
    datacenter: US
    type: IPV4

# Delete a public IP

- oneandone_public_ip:
    auth_token: oneandone_private_api_key
    ip_id: 8D135204687B9CF9E79E7A93C096E336

'''

from copy import copy
import time

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

DATACENTERS = ['US', 'ES', 'DE', 'GB']

TYPES = ['IPV4', 'IPV6']


def _find_datacenter(oneandone_conn, datacenter_id):
    """
    Given datacenter_id, validates the datacenter exists whether
    it is a proper ID or name. If the datacenter cannot be found,
    return none.
    """
    datacenter = None
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter_id in (_datacenter['id'], _datacenter['country_code']):
            datacenter = _datacenter
            break
    return datacenter


def _wait_for_public_ip_creation_completion(oneandone_conn,
                                          public_ip, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the public IP info
        public_ip = oneandone_conn.get_public_ip(public_ip['id'])

        if public_ip['state'].lower() == 'active':
            return
        elif public_ip['state'].lower() == 'failed':
            raise Exception('Public IP creation ' +
                            ' failed for %' % public_ip['id'])
        elif public_ip['state'].lower() in ('active',
                                            'configuring'):
            continue
        else:
            raise Exception(
                'Unknown public IP state %s' % public_ip['state'])

    raise Exception(
        'Timed out waiting for public IP competion for %s' % public_ip['id'])


def create_public_ip(module, oneandone_conn):
    """
    Create new public IP

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any public IP was added.
    """
    reverse_dns = module.params.get('reverse_dns')
    datacenter_id = module.params.get('datacenter')
    type = module.params.get('type')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    if datacenter_id is not None:
        datacenter = _find_datacenter(oneandone_conn, datacenter_id)
        if datacenter is None:
            module.fail_json(
                msg='datacenter %s not found.' % datacenter_id)

    try:
        public_ip = oneandone_conn.create_public_ip(
            reverse_dns=reverse_dns,
            ip_type=type,
            datacenter_id=datacenter['id'])

        if wait:
            _wait_for_public_ip_creation_completion(
                oneandone_conn, public_ip, wait_timeout)
            public_ip = oneandone_conn.get_public_ip(public_ip['id'])  # refresh

        return public_ip
    except Exception as e:
        module.fail_json(msg=str(e))

def update_public_ip(module, oneandone_conn):
    """
    Update a public IP

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any public IP was changed.
    """
    reverse_dns = module.params.get('reverse_dns')
    public_ip_id = module.params.get('id')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    public_ip = oneandone_conn.get_public_ip(oneandone_conn, public_ip_id)
    if public_ip is None:
        module.fail_json(
            msg='public IP %s not found.' % public_ip_id)

    try:
        public_ip = oneandone_conn.modify_public_ip(
            ip_id=public_ip_id,
            reverse_dns=reverse_dns)

        if wait:
            _wait_for_public_ip_creation_completion(
                oneandone_conn, public_ip, wait_timeout)
            public_ip = oneandone_conn.get_public_ip(public_ip['id'])  # refresh

        return public_ip
    except Exception as e:
        module.fail_json(msg=str(e))

def delete_public_ip(module, oneandone_conn):
    """
    Delete a public IP

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any public IP was deleted.
    """
    public_ip_id = module.params.get('id')

    public_ip = oneandone_conn.get_public_ip(oneandone_conn, public_ip_id)
    if public_ip is None:
        module.fail_json(
            msg='public IP %s not found.' % public_ip_id)

    try:
        public_ip = oneandone_conn.delete_public_ip(
            ip_id=public_ip_id)

        return public_ip
    except Exception as e:
        module.fail_json(msg=str(e))

def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            reverse_dns=dict(type='str'),
            datacenter=dict(
                choices=DATACENTERS,
                default='US'),
            type=dict(
                choices=TYPES,
                default='IPV4'),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            state=dict(type='str', default='present'),
        )
    )

    if not HAS_ONEANDONE_SDK:
        module.fail_json(msg='1and1 required for this module')

    if not module.params.get('auth_token'):
        module.fail_json(
            msg='auth_token parameter is required.')

    auth_token = module.params.get('auth_token')

    oneandone_conn = oneandone.client.OneAndOneService(
        api_token=auth_token)

    state = module.params.get('state')

    if state == 'absent':
        try:
            module.exit_json(**delete_public_ip(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            module.exit_json(**update_public_ip(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state in ('present'):
        try:
            module.exit_json(**create_public_ip(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
