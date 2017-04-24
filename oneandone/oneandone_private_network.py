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
module: oneandone_private_network
short_description: Configure 1&1 private networking.
description:
     - Create, remove, reconfigure, update a private network
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  state:
    description:
      - Define a network's state to create, remove, reconfigure, or update.
    required: false
    default: 'present'
    choices: [ "present", "absent", "reconfigure", "update" ]
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - The name or ID of the network.
    required: true
  description:
    description:
      - Set a description for the network.
  network_address:
    description:
      - Set a private network space, i.e. 192.168.1.0
  subnet_mask:
    description:
      - Set the netmask for the private network, i.e. 255.255.255.0
  add_members:
    description:
      - Used when adding a member.
  remove_members:
    description:
      - Used when removing a member.

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (@aajdinov)
'''

EXAMPLES = '''

# Provisioning example. Create and destroy private networks.

- oneandone_private_network:
    auth_token: oneandone_private_api_key
    name: backup_network
    datacenter: US
    network_address: 192.168.1.0
    subnet_mask: 255.255.255.0

- oneandone_private_network:
    auth_token: oneandone_private_api_key
    state: absent
    name: backup_network

# Modify the private network.

- oneandone_private_network:
    auth_token: oneandone_private_api_key
    state: reconfigure
    name: backup_network
    network_address: 192.168.2.0
    subnet_mask: 255.255.255.0

# Add members to the private network.

- oneandone_private_network:
    auth_token: oneandone_private_api_key
    state: update
    name: backup_network
    add_members: host01

# Remove members from the private network.

- oneandone_private_network:
    auth_token: oneandone_private_api_key
    state: update
    name: backup_network
    remove_members: host01

'''

RETURN = '''
changed:
    description: True if a machine created, modified or removed
    type: bool
    sample: True
    returned: always
private_network:
    description: Information about the private network.
    type: array
    sample: '[{"name": "backup_network", "id": "55726DEDA20C99CF6F2AF8F18CAC9963"}]'
    returned: always
'''

from copy import copy
import time

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

DATACENTERS = ['US', 'ES', 'DE', 'GB']


def _find_datacenter(oneandone_conn, datacenter):
    """
    Validates the datacenter exists by ID or country code.
    Returns the datacenter ID.
    """
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter in (_datacenter['id'], _datacenter['country_code']):
            return _datacenter['id']


def _find_private_network(oneandone_conn, private_network):
    """
    Validates the private network exists by ID or name.
    Return the private network if one was found.
    """
    for _private_network in oneandone_conn.list_private_networks(per_page=1000):
        if private_network in (_private_network['id'], _private_network['name']):
            return _private_network


def _wait_for_network_creation_completion(oneandone_conn,
                                          network, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the network info
        network = oneandone_conn.get_private_network(network['id'])

        if network['state'].lower() == 'active':
            return
        elif network['state'].lower() == 'failed':
            raise Exception('Private network creation ' +
                            ' failed for %s' % network['id'])
        elif network['state'].lower() in ('active',
                                          'enabled',
                                          'deploying',
                                          'configuring'):
            continue
        else:
            raise Exception(
                'Unknown network state %s' % network['state'])

    raise Exception(
        'Timed out waiting for network competion for %s' % network['id'])


def _find_machine(oneandone_conn, instance):
    """
    Validates that the machine exists whether by ID or name.
    Returns the machine if one was found.
    """
    for _machine in oneandone_conn.list_servers(per_page=1000):
        if instance in (_machine['id'], _machine['name']):
            return _machine


def _add_member(module, oneandone_conn, name, members):
    """
    """

    try:
        o = oneandone_conn

        network = o.attach_private_network_servers(private_network_id=name,
                                                   server_ids=members)

        return network
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_member(module, oneandone_conn, name, member_id):
    """
    """

    try:
        o = oneandone_conn

        network = o.remove_private_network_server(private_network_id=name,
                                                  server_id=member_id)

        return network
    except Exception as e:
        module.fail_json(msg=str(e))


def addremove_member(module, oneandone_conn):
    """
    Adds or removes a member from a private network

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any member was added.
    """
    try:
        name = module.params.get('name')
        add_members = module.params.get('add_members')
        remove_members = module.params.get('remove_members')
        private_network = _find_private_network(oneandone_conn, name)
        network = None

        changed = False

        if add_members:
            instances = []

            for member in add_members:
                instance = _find_machine(oneandone_conn, member)
                instance_obj = oneandone.client.AttachServer(server_id=instance['id'])

                instances.extend([instance_obj])
            network = _add_member(module, oneandone_conn, private_network['id'], instances)
            changed = True if network else False

        if remove_members:
            for member in remove_members:
                instance = _find_machine(oneandone_conn, member)
                _remove_member(module,
                               oneandone_conn,
                               private_network['id'],
                               instance['id'])
            network = _find_private_network(oneandone_conn, name)
            changed = True if network else False

        return (changed, network)
    except Exception as e:
        module.fail_json(msg=str(e))


def create_network(module, oneandone_conn):
    """
    Create new private network

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any network was added.
    """
    name = module.params.get('name')
    description = module.params.get('description')
    network_address = module.params.get('network_address')
    subnet_mask = module.params.get('subnet_mask')
    datacenter = module.params.get('datacenter')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    if datacenter is not None:
        datacenter_id = _find_datacenter(oneandone_conn, datacenter)
        if datacenter_id is None:
            module.fail_json(
                msg='datacenter %s not found.' % datacenter)

    try:
        network = oneandone_conn.create_private_network(
            private_network=oneandone.client.PrivateNetwork(
                name=name,
                description=description,
                network_address=network_address,
                subnet_mask=subnet_mask,
                datacenter_id=datacenter_id
            ))

        if wait:
            _wait_for_network_creation_completion(
                oneandone_conn,
                network,
                wait_timeout)
            network = _find_private_network(oneandone_conn,
                                            network['id'])

        changed = True if network else False

        return (changed, network)
    except Exception as e:
        module.fail_json(msg=str(e))


def update_network(module, oneandone_conn):
    """
    Modifies a private network.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    _private_network_id = module.params.get('private_network_id')
    _name = module.params.get('name')
    _description = module.params.get('description')
    _network_address = module.params.get('network_address')
    _subnet_mask = module.params.get('subnet_mask')

    try:
        network = oneandone_conn.modify_private_network(
            private_network_id=_private_network_id,
            name=_name,
            description=_description,
            network_address=_network_address,
            subnet_mask=_subnet_mask)

        changed = True if network else False

        return (changed, network)
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_network(module, oneandone_conn):
    """
    Removes a private network.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object.
    """
    try:
        name = module.params.get('name')
        private_network = _find_private_network(oneandone_conn, name)
        private_network = oneandone_conn.delete_private_network(private_network['id'])

        changed = True if private_network else False

        return (changed, {
            'id': private_network['id'],
            'name': private_network['name']
        })
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            name=dict(type='str'),
            description=dict(type='str'),
            network_address=dict(type='str'),
            subnet_mask=dict(type='str'),
            add_members=dict(type='list', default=[]),
            remove_members=dict(type='list', default=[]),
            datacenter=dict(
                choices=DATACENTERS),
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
            (changed, private_network) = remove_network(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            (changed, private_network) = update_network(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'add_remove_member':
        try:
            (changed, private_network) = addremove_member(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name',):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new networks." % param)
        try:
            (changed, private_network) = create_network(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=changed, private_network=private_network)


from ansible.module_utils.basic import *

main()
