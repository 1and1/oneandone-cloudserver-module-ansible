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
     - Create, update, and remove public IPs.
       This module has a dependency on 1and1 >= 1.0
version_added: "2.4"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  api_url:
    description:
      - Custom API URL. Overrides the
        ONEANDONE_API_URL environement variable.
    required: false  
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
  public_ip_id:
    description:
      - The ID of the public IP used with update and delete states.
    required: true
  wait:
    description:
      - wait for the instance to be in state 'running' before returning
    required: false
    default: "yes"
    choices: [ "yes", "no" ]
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 600
  wait_interval:
    description:
      - Defines the number of seconds to wait when using the _wait_for methods
    default: 5  

requirements:
     - "1and1"
     - "python >= 2.6"

author:
  - Amel Ajdinovic (@aajdinov)
  - Ethan Devenport (@edevenport)
'''

EXAMPLES = '''

# Create a public IP.

- oneandone_public_ip:
    auth_token: oneandone_private_api_key
    reverse_dns: example.com
    datacenter: US
    type: IPV4

# Update a public IP.

- oneandone_public_ip:
    auth_token: oneandone_private_api_key
    public_ip_id: public ip id
    reverse_dns: secondexample.com
    state: update


# Delete a public IP

- oneandone_public_ip:
    auth_token: oneandone_private_api_key
    public_ip_id: public ip id
    state: absent

'''

import os
import time
from ansible.module_utils.basic import AnsibleModule

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

DATACENTERS = ['US', 'ES', 'DE', 'GB']

TYPES = ['IPV4', 'IPV6']


def _find_datacenter(oneandone_conn, datacenter):
    """
    Validates the datacenter exists by ID or country code.
    Returns the datacenter ID.
    """
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter in (_datacenter['id'], _datacenter['country_code']):
            return _datacenter['id']


def _wait_for_public_ip_creation_completion(oneandone_conn,
                                            public_ip, wait_timeout, wait_interval):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(wait_interval)

        # Refresh the public IP info
        public_ip = oneandone_conn.get_public_ip(public_ip['id'])

        if public_ip['state'].lower() == 'active':
            return
        elif public_ip['state'].lower() == 'failed':
            raise Exception('Public IP creation ' +
                            ' failed for %s' % public_ip['id'])
        elif public_ip['state'].lower() == 'configuring':
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
    datacenter = module.params.get('datacenter')
    ip_type = module.params.get('type')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    wait_interval = module.params.get('wait_interval')

    if datacenter is not None:
        datacenter_id = _find_datacenter(oneandone_conn, datacenter)
        if datacenter_id is None:
            module.fail_json(
                msg='datacenter %s not found.' % datacenter)

    try:
        public_ip = oneandone_conn.create_public_ip(
            reverse_dns=reverse_dns,
            ip_type=ip_type,
            datacenter_id=datacenter_id)

        if wait:
            _wait_for_public_ip_creation_completion(
                oneandone_conn, public_ip, wait_timeout, wait_interval)
            public_ip = oneandone_conn.get_public_ip(public_ip['id'])

        changed = True if public_ip else False

        return (changed, public_ip)
    except Exception as ex:
        module.fail_json(msg=str(ex))


def update_public_ip(module, oneandone_conn):
    """
    Update a public IP

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any public IP was changed.
    """
    reverse_dns = module.params.get('reverse_dns')
    public_ip_id = module.params.get('public_ip_id')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    wait_interval = module.params.get('wait_interval')

    changed = False

    public_ip = oneandone_conn.get_public_ip(ip_id=public_ip_id)
    if public_ip is None:
        module.fail_json(
            msg='public IP %s not found.' % public_ip_id)

    try:
        public_ip = oneandone_conn.modify_public_ip(
            ip_id=public_ip_id,
            reverse_dns=reverse_dns)

        changed = True

        if wait:
            _wait_for_public_ip_creation_completion(
                oneandone_conn, public_ip, wait_timeout, wait_interval)
            public_ip = oneandone_conn.get_public_ip(public_ip['id'])

        return (changed, public_ip)
    except Exception as ex:
        module.fail_json(msg=str(ex))


def delete_public_ip(module, oneandone_conn):
    """
    Delete a public IP

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any public IP was deleted.
    """
    public_ip_id = module.params.get('public_ip_id')

    public_ip = oneandone_conn.get_public_ip(public_ip_id)
    if public_ip is None:
        module.fail_json(
            msg='public IP %s not found.' % public_ip_id)

    try:
        public_ip = oneandone_conn.delete_public_ip(
            ip_id=public_ip_id)

        changed = True if public_ip else False

        return (changed, {
            'id': public_ip['id']
        })
    except Exception as ex:
        module.fail_json(msg=str(ex))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            api_url=dict(
                type='str',
                default=os.environ.get('ONEANDONE_API_URL')),
            public_ip_id=dict(type='str'),
            reverse_dns=dict(type='str'),
            datacenter=dict(
                choices=DATACENTERS,
                default='US'),
            type=dict(
                choices=TYPES,
                default='IPV4'),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            wait_interval=dict(type='int', default=5),
            state=dict(type='str', default='present'),
        )
    )

    if not HAS_ONEANDONE_SDK:
        module.fail_json(msg='1and1 required for this module')

    if not module.params.get('auth_token'):
        module.fail_json(
            msg='auth_token parameter is required.')

    if not module.params.get('api_url'):
        oneandone_conn = oneandone.client.OneAndOneService(
            api_token=module.params.get('auth_token'))
    else:
        oneandone_conn = oneandone.client.OneAndOneService(
            api_token=module.params.get('auth_token'), api_url=module.params.get('api_url'))

    state = module.params.get('state')

    if state == 'absent':
        if not module.params.get('public_ip_id'):
            module.fail_json(
                msg="'public_ip_id' parameter is required to delete a public ip.")
        try:
            (changed, public_ip) = delete_public_ip(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))
    elif state == 'update':
        if not module.params.get('public_ip_id'):
            module.fail_json(
                msg="'public_ip_id' parameter is required to update a public ip.")
        try:
            (changed, public_ip) = update_public_ip(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))

    elif state == 'present':
        try:
            (changed, public_ip) = create_public_ip(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))

    module.exit_json(changed=changed, public_ip=public_ip)


if __name__ == '__main__':
    main()
