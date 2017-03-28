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

DOCUMENTATION = '''
---
module: oneandone_firewall_policy
short_description: Configure 1&1 firewall policy.
description:
     - Create, remove, reconfigure, update firewall policies
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - Firewall policy name.
    required: true
    maxLength: 128
  port_from:
    description:
      - First port in range. Required for UDP and TCP protocols, otherwise it will be set up automatically.
    required: false
    minimum: 1
    maximum: 65535
  port_to:
    description:
      - Second port in range. Required for UDP and TCP protocols, otherwise it will be set up automatically.
  protocol:
    description:
      - Internet protocol
      choices: [ "TCP", "UDP", "ICMP", "AH", "ESP", "GRE" ]
      required: true
  source:
    description:
      - IPs from which access is available. Setting 0.0.0.0 all IPs are allowed.
    default: 0.0.0.0
    required: false
  description:
    description:
      - Firewall policy description.
    maxLength: 256
    required: false

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (amel@stackpointcloud.com)
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

# Reconfigure the private network.

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

from copy import copy
import time

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False


def _wait_for_firewall_policy_creation_completion(oneandone_conn, firewall_policy, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the network info
        firewall_policy = oneandone_conn.get_firewall(firewall_policy['id'])

        if firewall_policy['state'].lower() == 'active':
            return
        elif firewall_policy['state'].lower() == 'failed':
            raise Exception('Private network creation ' +
                            ' failed for %' % firewall_policy['id'])
        elif firewall_policy['state'].lower() in ('active',
                                                  'enabled',
                                                  'deploying',
                                                  'configuring'):
            continue
        else:
            raise Exception(
                'Unknown network state %s' % firewall_policy['state'])

    raise Exception(
        'Timed out waiting for network competion for %s' % firewall_policy['id'])


def _find_firewall_policy(oneandone_conn, name):
    """
    Given a name, validates that the network exists
    whether it is a proper ID or a name.
    Returns the network if one was found, else None.
    """
    firewall_policy = None
    firewall_policies = oneandone_conn.list_firewall_policies(per_page=1000)
    for _firewall_policy in firewall_policies:
        if name in (_firewall_policy['id'], _firewall_policy['name']):
            firewall_policy = _firewall_policy
            break
    return firewall_policy


def _find_machine(oneandone_conn, instance_id):
    """
    Given a instance_id, validates that the machine exists
    whether it is a proper ID or a name.
    Returns the machine if one was found, else None.
    """
    machine = None
    machines = oneandone_conn.list_servers(per_page=1000)
    for _machine in machines:
        if instance_id in (_machine['id'], _machine['name']):
            machine = _machine
            break
    return machine



def _add_server_ips(module, oneandone_conn, firewall_id, server_ids):
    """
    Assigns servers to a firewall policy.
    """
    try:
        attach_servers = []

        for _server_id in server_ids:
            server = _find_machine(oneandone_conn, _server_id)
            attach_server = oneandone.client.AttachServer(
                server_id=server['id'],
                server_ip_id=next(iter(server['ips'] or []), None)['id']
            )
            attach_servers.append(attach_server)

        firewall_policy = oneandone_conn.attach_server_firewall_policy(
            firewall_id=firewall_id,
            server_ips=attach_servers)
        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_firewall_server(module, oneandone_conn, firewall_id, server_ip_id):
    """
    Unassigns a server/IP from a firewall policy.
    """
    try:
        firewall_policy = oneandone_conn.remove_firewall_server(firewall_id=firewall_id, server_ip_id=server_ip_id)
        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def _add_firewall_rules(module, oneandone_conn, firewall_id, rules):
    """
    Adds new rules to a firewall policy.
    """
    try:
        firewall_rules = []

        for rule in rules:
            firewall_rule = oneandone.client.FirewallPolicyRule(
                protocol=rule['protocol'],
                port_from=rule['port_from'],
                port_to=rule['port_to'],
                source=rule['source'])
            firewall_rules.append(firewall_rule)

        firewall_policy = oneandone_conn.add_firewall_policy_rule(
            firewall_id=firewall_id,
            firewall_policy_rules=firewall_rules
        )
        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_firewall_rule(module, oneandone_conn, firewall_id, rule_id):
    """
    Removes a rule from a firewall policy.
    """
    try:
        firewall_policy = oneandone_conn.remove_firewall_rule(
            firewall_id=firewall_id,
            rule_id=rule_id
        )
        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def update_firewall_policy(module, oneandone_conn):
    """
    Updates a firewall policy based on input arguments.
    Firewall rules and server ips can be added/removed to/from
    firewall policy. Firewall policy name and description can be
    updated as well.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    name = module.params.get('name')
    description = module.params.get('description')
    add_server_ips = module.params.get('add_server_ips')
    remove_server_ips = module.params.get('remove_server_ips')
    add_rules = module.params.get('add_rules')
    remove_rules = module.params.get('remove_rules')

    firewall_policy = _find_firewall_policy(oneandone_conn, name)

    if name or description:
        firewall_policy = oneandone_conn.modify_firewall(
            firewall_id=firewall_policy['id'],
            name=name,
            description=description)

    if add_server_ips:
        firewall_policy = _add_server_ips(module, oneandone_conn, firewall_policy['id'], add_server_ips)

    if remove_server_ips:
        for server_ip_id in remove_server_ips:
            _remove_firewall_server(module,
                                    oneandone_conn,
                                    firewall_policy['id'],
                                    server_ip_id)
            firewall_policy = _find_firewall_policy(oneandone_conn, firewall_policy['id'])

    if add_rules:
        firewall_policy = _add_firewall_rules(module,
                                              oneandone_conn,
                                              firewall_policy['id'],
                                              add_rules)

    if remove_rules:
        for rule_id in remove_rules:
            _remove_firewall_rule(module,
                                  oneandone_conn,
                                  firewall_policy['id'],
                                  rule_id)
            firewall_policy = _find_firewall_policy(oneandone_conn, firewall_policy['id'])

    try:
        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def create_firewall_policy(module, oneandone_conn):
    """
    Create a new firewall policy.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        description = module.params.get('description')
        rules = module.params.get('rules')
        wait = module.params.get('wait')
        wait_timeout = module.params.get('wait_timeout')

        firewall_rules = []

        for rule in rules:
            firewall_rule = oneandone.client.FirewallPolicyRule(
                protocol=rule['protocol'],
                port_from=rule['port_from'],
                port_to=rule['port_to'],
                source=rule['source'])
            firewall_rules.append(firewall_rule)

        firewall_policy_obj = oneandone.client.FirewallPolicy(
            name=name,
            description=description
        )

        firewall_policy = oneandone_conn.create_firewall_policy(
            firewall_policy=firewall_policy_obj,
            firewall_policy_rules=firewall_rules
        )

        if wait:
            _wait_for_firewall_policy_creation_completion(
                oneandone_conn, firewall_policy, wait_timeout)

        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_firewall_policy(module, oneandone_conn):
    """
    Removes a firewall policy.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        firewall_policy = _find_firewall_policy(oneandone_conn, name)
        firewall_policy = oneandone_conn.delete_firewall(firewall_policy['id'])

        return firewall_policy
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(type='str'),
            name=dict(type='str'),
            description=dict(type='str'),
            rules=dict(type='list', default=[]),
            add_server_ips=dict(type='list', default=[]),
            remove_server_ips=dict(type='list', default=[]),
            add_rules=dict(type='list', default=[]),
            remove_rules=dict(type='list', default=[]),
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
            module.exit_json(**remove_firewall_policy(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            module.exit_json(**update_firewall_policy(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name',):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new networks." % param)
        try:
            module.exit_json(**create_firewall_policy(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
