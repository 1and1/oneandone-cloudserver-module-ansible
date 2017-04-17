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
module: oneandone_vpn
short_description: Configure 1&1 VPN.
description:
     - Create, remove, update vpn
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - VPN name.
    maxLength: 128
    required: true
  description:
    description:
      - VPN description.
    maxLength: 256
    required: false
  datacenter_id:
    description:
      - ID (or name) of the datacenter where the vpn will be created.
    required: false

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (@aajdinov)
'''

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

def _wait_for_vpn_creation_completion(oneandone_conn, vpn, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the vpn info
        vpn = oneandone_conn.get_vpn(vpn['id'])

        if vpn['state'].lower() == 'active':
            return
        elif vpn['state'].lower() == 'failed':
            raise Exception('VPN creation ' +
                            ' failed for %s' % vpn['id'])
        elif vpn['state'].lower() in ('active',
                                      'enabled',
                                      'deploying',
                                      'configuring'):
            continue
        else:
            raise Exception(
                'Unknown VPN state %s' % vpn['state'])

    raise Exception(
        'Timed out waiting for VPN competion for %s' % vpn['id'])


def _find_vpn(oneandone_conn, vpn):
    """
    Validates that the vpn exists by ID or a name.
    Returns the vpn if one was found.
    """
    for _vpn in oneandone_conn.list_vpns(per_page=1000):
        if vpn in (_vpn['id'], _vpn['name']):
            return _vpn


def _find_datacenter(oneandone_conn, datacenter):
    """
    Validates the datacenter exists by ID or country code.
    Returns the datacenter ID.
    """
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter in (_datacenter['id'], _datacenter['country_code']):
            return _datacenter['id']


def update_vpn(module, oneandone_conn):
    """
    Modify VPN configuration file.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    _vpn = module.params.get('vpn')
    _name = module.params.get('name')
    _description = module.params.get('description')

    vpn = _find_vpn(oneandone_conn, _vpn)

    try:
        vpn = oneandone_conn.modify_vpn(vpn['id'], name=_name, description=_description)

        return vpn
    except Exception as e:
        module.fail_json(msg=str(e))


def create_vpn(module, oneandone_conn):
    """
    Adds a new VPN.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        description = module.params.get('description')
        datacenter = module.params.get('datacenter')
        wait = module.params.get('wait')
        wait_timeout = module.params.get('wait_timeout')

        if datacenter is not None:
            datacenter_id = _find_datacenter(oneandone_conn, datacenter)
            if datacenter_id is None:
                module.fail_json(
                    msg='datacenter %s not found.' % datacenter)

        _vpn = oneandone.client.Vpn(name,
                                    description,
                                    datacenter_id)

        vpn = oneandone_conn.create_vpn(_vpn)

        if wait:
            _wait_for_vpn_creation_completion(
                oneandone_conn,
                vpn,
                wait_timeout)

        return vpn
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_vpn(module, oneandone_conn):
    """
    Removes a VPN.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        _vpn = module.params.get('vpn')
        vpn = _find_vpn(oneandone_conn, _vpn)
        vpn = oneandone_conn.delete_vpn(vpn['id'])

        return vpn
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            vpn=dict(type='str'),
            name=dict(type='str'),
            description=dict(type='str'),
            datacenter=dict(type='str'),
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
            module.exit_json(**remove_vpn(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            module.exit_json(**update_vpn(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        if not module.params.get('name'):
            module.fail_json(
                msg="name parameter is required for a new VPN.")
        try:
            module.exit_json(**create_vpn(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
