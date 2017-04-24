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
module: oneandone_load_balancer
short_description: Configure 1&1 load balancer.
description:
     - Create, remove, update load balancers
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - Load balancer name.
    required: true
    maxLength: 128
  health_check_test:
    description:
      - Type of the health check. At the moment, HTTP is not allowed.
    choices: [ "NONE", "TCP", "HTTP", "ICMP" ]
    required: true
  health_check_interval:
    description:
      - Health check period in seconds.
    minimum: 5
    maximum: 300
    multipleOf: 1
    required: true
  health_check_path:
    description:
      - Url to call for cheking. Required for HTTP health check.
    maxLength: 1000
    required: false
  health_check_parser:
    description:
      - Regular expression to check. Required for HTTP health check.
    maxLength: 64
    required: false
  persistence:
    description:
      - Persistence.
    required: true
  persistence_time:
    description:
      - Persistence time in seconds. Required if persistence is enabled.
    minimum: 30
    maximum: 1200
    multipleOf: 1
    required: true
  method:
    description:
      - Balancing procedure.
    choices: [ "ROUND_ROBIN", "LEAST_CONNECTIONS" ]
    required: true
  datacenter:
    description:
      - ID or country code of the datacenter where the load balancer will be created.
    default: US
    choices: [ "US", "ES", "DE", "GB" ]
    required: false
  protocol:
    description:
      - Internet protocol
      choices: [ "TCP", "UDP" ]
      required: true
  port_balancer:
    description:
      - Port in balancer. Port 0 means every port.
        Only can be used if also 0 is set in port_server and health_check_test is set to NONE or ICMP.
    minimum: 0
    maximum: 65535
    required: true
  port_server:
    description:
      - Port in server. Port 0 means every port.
        Only can be used if also 0 is set in port_balancer and health_check_test is set to NONE or ICMP.
    minimum: 0
    maximum: 65535
    required: true
  source:
    description:
      - IPs from which access is available. Setting 0.0.0.0 all IPs are allowed.
    default: 0.0.0.0
    required: false
  description:
    description:
      - Description of the load balancer.
    maxLength: 256
    required: false

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (@aajdinov)
'''

from copy import copy
import time

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

DATACENTERS = ['US', 'ES', 'DE', 'GB']
HEALTH_CHECK_TESTS = ['NONE', 'TCP', 'HTTP', 'ICMP']
METHODS = ['ROUND_ROBIN', 'LEAST_CONNECTIONS']

def _wait_for_load_balancer_creation_completion(oneandone_conn, load_balancer, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the load balancer info
        load_balancer = oneandone_conn.get_load_balancer(load_balancer['id'])

        if load_balancer['state'].lower() == 'active':
            return
        elif load_balancer['state'].lower() == 'failed':
            raise Exception('Load balancer creation ' +
                            ' failed for %s' % load_balancer['id'])
        elif load_balancer['state'].lower() in ('active',
                                                'enabled',
                                                'deploying',
                                                'configuring'):
            continue
        else:
            raise Exception(
                'Unknown load balancer state %s' % load_balancer['state'])

    raise Exception(
        'Timed out waiting for load balancer competion for %s' % load_balancer['id'])


def _find_load_balancer(oneandone_conn, load_balancer):
    """
    Given a name, validates that the load balancer exists
    whether it is a proper ID or a name.
    Returns the load_balancer if one was found, else None.
    """
    for _load_balancer in oneandone_conn.list_load_balancers(per_page=1000):
        if load_balancer in (_load_balancer['id'],
                             _load_balancer['name']):
            return _load_balancer


def _find_datacenter(oneandone_conn, datacenter):
    """
    Validates the datacenter exists by ID or name.
    Returns the datacenter ID.
    """
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter in (_datacenter['id'], _datacenter['country_code']):
            return _datacenter['id']


def _add_server_ips(module, oneandone_conn, load_balancer_id, server_ips):
    """
    Assigns servers to a load balancer.
    """
    try:
        attach_servers = []

        for server_ip in server_ips:
            attach_server = oneandone.client.AttachServer(
                server_ip_id=server_ip
            )
            attach_servers.append(attach_server)

        load_balancer = oneandone_conn.attach_load_balancer_server(
            load_balancer_id=load_balancer_id,
            server_ips=attach_servers)
        return load_balancer
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_load_balancer_server(module, oneandone_conn, load_balancer_id, server_ip_id):
    """
    Unassigns a server/IP from a load balancer.
    """
    try:
        load_balancer = oneandone_conn.remove_load_balancer_server(
            load_balancer_id=load_balancer_id,
            server_ip_id=server_ip_id)
        return load_balancer
    except Exception as e:
        module.fail_json(msg=str(e))


def _add_load_balancer_rules(module, oneandone_conn, load_balancer_id, rules):
    """
    Adds new rules to a load_balancer.
    """
    try:
        load_balancer_rules = []

        for rule in rules:
            load_balancer_rule = oneandone.client.LoadBalancerRule(
                protocol=rule['protocol'],
                port_balancer=rule['port_balancer'],
                port_server=rule['port_server'],
                source=rule['source'])
            load_balancer_rules.append(load_balancer_rule)

        load_balancer = oneandone_conn.add_load_balancer_rule(
            load_balancer_id=load_balancer_id,
            load_balancer_rules=load_balancer_rules
        )

        return load_balancer
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_load_balancer_rule(module, oneandone_conn, load_balancer_id, rule_id):
    """
    Removes a rule from a load_balancer.
    """
    try:
        load_balancer = oneandone_conn.remove_load_balancer_rule(
            load_balancer_id=load_balancer_id,
            rule_id=rule_id
        )
        return load_balancer
    except Exception as e:
        module.fail_json(msg=str(e))


def update_load_balancer(module, oneandone_conn):
    """
    Updates a load_balancer based on input arguments.
    Load balancer rules and server ips can be added/removed to/from
    load balancer. Load balancer name, description, health_check_test,
    health_check_interval, persistence, persistence_time, and method
    can be updated as well.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    name = module.params.get('name')
    description = module.params.get('description')
    health_check_test = module.params.get('health_check_test')
    health_check_interval = module.params.get('health_check_interval')
    health_check_path = module.params.get('health_check_path')
    health_check_parse = module.params.get('health_check_parse')
    persistence = module.params.get('persistence')
    persistence_time = module.params.get('persistence_time')
    method = module.params.get('method')
    add_server_ips = module.params.get('add_server_ips')
    remove_server_ips = module.params.get('remove_server_ips')
    add_rules = module.params.get('add_rules')
    remove_rules = module.params.get('remove_rules')

    changed = False

    load_balancer = _find_load_balancer(oneandone_conn, name)

    if (name or description or health_check_test or health_check_interval or health_check_path
        or health_check_parse or persistence or persistence_time or method):
        load_balancer = oneandone_conn.modify_load_balancer(
            load_balancer_id=load_balancer['id'],
            name=name,
            description=description,
            health_check_test=health_check_test,
            health_check_interval=health_check_interval,
            health_check_path=health_check_path,
            health_check_parse=health_check_parse,
            persistence=persistence,
            persistence_time=persistence_time,
            method=method)
        changed = True

    if add_server_ips:
        load_balancer = _add_server_ips(module, oneandone_conn, load_balancer['id'], add_server_ips)
        changed = True

    if remove_server_ips:
        for server_ip_id in remove_server_ips:
            _remove_load_balancer_server(module,
                                         oneandone_conn,
                                         load_balancer['id'],
                                         server_ip_id)
            load_balancer = _find_load_balancer(oneandone_conn, load_balancer['id'])
        changed = True

    if add_rules:
        load_balancer = _add_load_balancer_rules(module,
                                                 oneandone_conn,
                                                 load_balancer['id'],
                                                 add_rules)
        changed = True

    if remove_rules:
        for rule_id in remove_rules:
            _remove_load_balancer_rule(module,
                                       oneandone_conn,
                                       load_balancer['id'],
                                       rule_id)
            load_balancer = _find_load_balancer(oneandone_conn, load_balancer['id'])
        changed = True

    try:
        return (changed, load_balancer)
    except Exception as e:
        module.fail_json(msg=str(e))


def create_load_balancer(module, oneandone_conn):
    """
    Create a new load_balancer.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        description = module.params.get('description')
        health_check_test = module.params.get('health_check_test')
        health_check_interval = module.params.get('health_check_interval')
        health_check_path = module.params.get('health_check_path')
        health_check_parse = module.params.get('health_check_parse')
        persistence = module.params.get('persistence')
        persistence_time = module.params.get('persistence_time')
        method = module.params.get('method')
        datacenter = module.params.get('datacenter')
        rules = module.params.get('rules')
        wait = module.params.get('wait')
        wait_timeout = module.params.get('wait_timeout')

        load_balancer_rules = []

        if datacenter is not None:
            datacenter_id = _find_datacenter(oneandone_conn, datacenter)
            if datacenter_id is None:
                module.fail_json(
                    msg='datacenter %s not found.' % datacenter)

        for rule in rules:
            load_balancer_rule = oneandone.client.LoadBalancerRule(
                protocol=rule['protocol'],
                port_balancer=rule['port_balancer'],
                port_server=rule['port_server'],
                source=rule['source'])
            load_balancer_rules.append(load_balancer_rule)

        load_balancer_obj = oneandone.client.LoadBalancer(
            health_check_path=health_check_path,
            health_check_parse=health_check_parse,
            name=name,
            description=description,
            health_check_test=health_check_test,
            health_check_interval=health_check_interval,
            persistence=persistence,
            persistence_time=persistence_time,
            method=method,
            datacenter_id=datacenter_id
        )

        load_balancer = oneandone_conn.create_load_balancer(
            load_balancer=load_balancer_obj,
            load_balancer_rules=load_balancer_rules
        )

        if wait:
            _wait_for_load_balancer_creation_completion(
                oneandone_conn, load_balancer, wait_timeout)

        changed = True if load_balancer else False

        return (changed, load_balancer)
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_load_balancer(module, oneandone_conn):
    """
    Removes a load_balancer.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        load_balancer = _find_load_balancer(oneandone_conn, name)
        load_balancer = oneandone_conn.delete_load_balancer(load_balancer['id'])

        changed = True if load_balancer else False

        return (changed, {
            'id': load_balancer['id'],
            'name': load_balancer['name']
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
            health_check_test=dict(
                choices=HEALTH_CHECK_TESTS),
            health_check_interval=dict(type='str'),
            health_check_path=dict(type='str'),
            health_check_parse=dict(type='str'),
            persistence=dict(type='bool'),
            persistence_time=dict(type='str'),
            method=dict(
                choices=METHODS),
            datacenter=dict(
                choices=DATACENTERS),
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
            (changed, load_balancer) = remove_load_balancer(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            (changed, load_balancer) = update_load_balancer(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name','health_check_test','health_check_interval','persistence','persistence_time','method'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new networks." % param)
        try:
            (changed, load_balancer) = create_load_balancer(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=changed, load_balancer=load_balancer)


from ansible.module_utils.basic import *

main()
