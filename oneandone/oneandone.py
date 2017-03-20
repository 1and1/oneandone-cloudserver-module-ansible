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
module: oneandone
short_description: create, destroy, start, stop, and reboot a 1&1 Host machine.
description:
     - create, destroy, update, start, stop, and reboot a 1&1 Host machine.
       When the machine is created it can optionally wait for it to be
       'running' before returning.
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  state:
    description:
      - Define a machine's state to create, remove, start or stop it.
    required: false
    default: 'present'
    choices: [ "present", "absent", "running", "stopped" ]
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  hostname:
    description:
      - The hostname or ID of the machine. Only used when state is 'present'.
    required: true when state is 'present', false otherwise.
  appliance:
    description:
      - The operating system for the machine. This must be the appliance id.
    required: true for 'present' state, false otherwise
  fixed_instance_size:
    description:
      - The instance size for the machine.
    required: true for 'present' state, false otherwise
    choices: [ "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL" ]
  datacenter:
    description:
      - The datacenter location.
    required: false
    default: US
    choices: [ "US", "ES", "DE", "GB" ]
  instance_ids:
    description:
      - List of machine IDs or hostnames.
    required: false for 'running' state, true otherwise
  count:
    description:
      - The number of machines to create.
    required: false
    default: 1
  ssh_key:
    description:
      - User's public SSH key.
    required: false
    default: None
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
  auto_increment:
    description:
      - When creating multiple machines at once, whether to differentiate
        hostnames by appending a count after them or substituting the count
        where there is a %02d or %03d in the hostname string.
    default: yes
    choices: ["yes", "no"]

requirements:
     - "1and1"
     - "python >= 2.6"
author: Matt Baldwin (baldwin@stackpointcloud.com)
'''

EXAMPLES = '''

# Provisioning example. Creates three servers and enumerate their names.

- oneandone:
    auth_token: oneandone_private_api_key
    hostname: node%02d.stackpointcloud.com
    fixed_instance_size: XL
    datacenter: US
    appliance: C5A349786169F140BCBC335675014C08
    auto_increment: true
    count: 3

# Create three machines, passing in an ssh_key.

- oneandone:
    auth_token: oneandone_private_api_key
    hostname: node%02d.stackpointcloud.com
    fixed_instance_size: XL
    datacenter: ES
    appliance: C5A349786169F140BCBC335675014C08
    count: 3
    wait: yes
    wait_timeout: 600
    ssh_key: SSH_PUBLIC_KEY

# Removing machines

- oneandone:
    auth_token: oneandone_private_api_key
    state: absent
    instance_ids:
      - 'node01.stackpointcloud.com'
      - 'node02.stackpointcloud.com'
      - 'node03.stackpointcloud.com'

# Starting Machines.

- oneandone:
    auth_token: oneandone_private_api_key
    state: running
    instance_ids:
      - 'node01.stackpointcloud.com'
      - 'node02.stackpointcloud.com'
      - 'node03.stackpointcloud.com'

# Stopping Machines

- oneandone:
    auth_token: oneandone_private_api_key
    state: stopped
    instance_ids:
      - 'node01.stackpointcloud.com'
      - 'node02.stackpointcloud.com'
      - 'node03.stackpointcloud.com'

'''

RETURN = '''
changed:
    description: True if a machine created, modified or removed
    type: bool
    sample: True
    returned: always
machines:
    description: Information about each machine that was processed
    type: array
    sample: '[{"hostname": "my-server", "id": "server-id"}]'
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

ONEANDONE_MACHINE_STATES = (
    'DEPLOYING',
    'POWERED_OFF',
    'POWERED_ON',
    'POWERING_ON',
    'POWERING_OFF',
)


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


def _find_fixed_instance_size(oneandone_conn, fixed_instance_size_id):
    """
    Given datacenter_id, validates the datacenter exists whether
    it is a proper ID or name. If the datacenter cannot be found,
    return none.
    """
    fixed_instance_size = None
    for _fixed_instance_size in oneandone_conn.fixed_server_flavors():
        if fixed_instance_size_id in (_fixed_instance_size['id'],
                                      _fixed_instance_size['name']):
            fixed_instance_size = _fixed_instance_size
            break
    return fixed_instance_size


def _find_appliance(oneandone_conn, appliance_id):
    appliance = None

    for _appliance in oneandone_conn.list_appliances(q='IMAGE'):
        if appliance_id in (_appliance['id']):
            appliance = _appliance
            break
    return appliance


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


def _wait_for_machine_creation_completion(oneandone_conn,
                                          machine, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the machine info
        machine = oneandone_conn.get_server(machine['id'])

        if machine['status']['state'].lower() == 'powered_on':
            return
        elif machine['status']['state'].lower() == 'failed':
            raise Exception('Machine creation failed for %' % machine['id'])
        elif machine['status']['state'].lower() in ('active',
                                                    'enabled',
                                                    'deploying'):
            continue
        else:
            raise Exception(
                'Unknown machine state %s' % machine['status']['state'])

    raise Exception(
        'Timed out waiting for machine competion for %s' % machine['id'])


def _create_machine(module, oneandone_conn, hostname, fixed_instance_size,
                    datacenter, appliance, ssh_key, wait,
                    wait_timeout):

    try:
        machine = oneandone_conn.create_server(
            oneandone.client.Server(name=hostname,
                                    fixed_instance_size_id=fixed_instance_size,
                                    appliance_id=appliance,
                                    datacenter_id=datacenter,
                                    rsa_key=ssh_key))

        if wait:
            _wait_for_machine_creation_completion(
                oneandone_conn, machine, wait_timeout)
            machine = oneandone_conn.get_server(machine['id'])  # refresh

        return machine
    except Exception as e:
        module.fail_json(msg=str(e))


def _serialize_machine(machine):
    """
    Standard represenation for a machine as returned by various tasks::

        {
            'id': 'instance_id'
            'hostname': 'machine_hostname',
            'tags': [],
            'ip_addresses': [
                {
                    "address": "147.75.194.227",
                    "address_family": 4,
                },
                {
                    "address": "2604:1380:2:5200::3",
                    "address_family": 6,
                },
                {
                    "address": "10.100.11.129",
                    "address_family": 4,
                }
            ],
            "public_ipv4": "147.75.194.227",
            "public_ipv6": "2604:1380:2:5200::3",
        }

    """
    machine_data = {}
    machine_data['id'] = machine['id']
    machine_data['hostname'] = machine['name']
    machine_data['ip_addresses'] = [
        {
            'address': addr_data['ip'],
            'address_family': addr_data['type'],
        }
        for addr_data in machine['ips']
    ]
    # Also include each IPs as a key for easier lookup in roles.
    # Key names:
    # - public_ipv4
    # - public_ipv6
    for ipdata in machine_data['ip_addresses']:
        if ipdata['address_family'] == 'IPV6':
            machine_data['public_ipv6'] = ipdata['address']
        elif ipdata['address_family'] == 'IPV4':
            machine_data['public_ipv4'] = ipdata['address']
    return machine_data


def create_machine(module, oneandone_conn):
    """
    Create new machine

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object

    Returns a dictionary containing a 'changed' attribute indicating whether
    any machine was added, and a 'machines' attribute with the list of the
    created machines's hostname, id and ip addresses.
    """
    hostname = module.params.get('hostname')
    auto_increment = module.params.get('auto_increment')
    count = module.params.get('count')
    fixed_instance_size_id = module.params.get('fixed_instance_size')
    datacenter_id = module.params.get('datacenter')
    appliance_id = module.params.get('appliance')
    ssh_key = module.params.get('ssh_key')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    datacenter = _find_datacenter(oneandone_conn, datacenter_id)
    if datacenter is None:
        module.fail_json(
            msg='datacenter %s not found.' % datacenter_id)

    fixed_instance_size = _find_fixed_instance_size(
        oneandone_conn,
        fixed_instance_size_id)
    if fixed_instance_size is None:
        module.fail_json(
            msg='fixed_instance_size %s note found.' % fixed_instance_size_id)

    appliance = _find_appliance(oneandone_conn, appliance_id)
    if datacenter is None:
        module.fail_json(
            msg='datacenter %s not found.' % datacenter_id)

    if auto_increment:
        # If the name has %02d or %03d somewhere in the host name, drop the
        # increment count in that location
        if '%02d' in hostname or '%03d' in hostname:
            str_formatted_name = hostname
        # Otherwise, default to name-01, name-02, onwards
        else:
            # str_formatted_name = "%s-%%02d" % hostname
            str_formatted_name = "%s-%%01d" % hostname

        hostnames = [
            str_formatted_name % i
            for i in xrange(1, count + 1)
        ]

    else:
        hostnames = [hostname] * count

    machines = []
    for name in hostnames:
        machines.append(
            _create_machine(
                module=module,
                oneandone_conn=oneandone_conn,
                hostname=name,
                fixed_instance_size=fixed_instance_size['id'],
                datacenter=datacenter['id'],
                appliance=appliance['id'],
                ssh_key=ssh_key,
                wait=wait,
                wait_timeout=wait_timeout))

    return {
        'changed': True if machines else False,
        'machines': [_serialize_machine(machine) for machine in machines],
    }


def remove_machine(module, oneandone_conn):
    """
    Remove machines.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object.

    Returns a dictionary containing a 'changed' attribute indicating whether
    any machines were removed, and a 'machines' attribute with the list of the
    removed machines's hostname and id.
    """
    instance_ids = module.params.get('instance_ids')

    if not isinstance(instance_ids, list) or len(instance_ids) < 1:
        module.fail_json(
            msg='instance_ids should be a list of machine ids or names.')

    removed_machines = []
    for instance_id in instance_ids:
        machine = _find_machine(oneandone_conn, instance_id)
        if machine is None:
            continue

        try:
            oneandone_conn.delete_server(server_id=machine['id'])
            removed_machines.append(machine)
        except Exception as e:
            module.fail_json(
                msg="failed to terminate the machine: %s" % str(e))

    return {
        'changed': True if removed_machines else False,
        'machines': [{
            'id': machine['id'],
            'hostname': machine['name'],
        } for machine in removed_machines]
    }


def startstop_machine(module, oneandone_conn):
    """
    Starts or Stops a machine.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object.

    Returns a dictionary with a 'changed' attribute indicating whether
    anything has changed for any of the machines as a result of this function
    being run, and a 'machines' attribute with basic information for
    each machine.
    """
    state = module.params.get('state')
    instance_ids = module.params.get('instance_ids')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    if not isinstance(instance_ids, list) or len(instance_ids) < 1:
        module.fail_json(
            msg='instance_ids should be a list of virtual ' +
                'machine ids or names.')

    machines = []
    changed = False
    for instance_id in instance_ids:

        # Resolve machine
        machine = _find_machine(oneandone_conn, instance_id)
        if machine is None:
            continue

        # Attempt to change the machine state, only if it's not already there
        # or on its way.
        try:
            if state == 'stopped':
                if machine['status']['state'] in ('POWERED_OFF'):
                    machines.append(machine)
                    continue
                oneandone_conn.modify_server_status(
                    server_id=machine['id'],
                    action='POWER_OFF',
                    method='SOFTWARE')
            elif state == 'running':
                if machine['status']['state'] in ('POWERED_ON'):
                    machines.append(machine)
                    continue
                oneandone_conn.modify_server_status(
                    server_id=machine['id'],
                    action='POWER_ON',
                    method='SOFTWARE')
        except Exception as e:
            module.fail_json(
                msg="failed to set machine %s to state %s: %s" % (
                    instance_id, state, str(e)))

        # Make sure the machine has reached the desired state
        if wait:
            operation_completed = False
            wait_timeout = time.time() + wait_timeout
            while wait_timeout > time.time():
                time.sleep(5)
                machine = oneandone_conn.get_server(machine['id'])  # refresh
                if state == 'stopped' and machine['status']['state'] == 'POWERED_OFF':
                    operation_completed = True
                    break
                if state == 'running' and machine['status']['state'] == 'POWERED_ON':
                    operation_completed = True
                    break
            if not operation_completed:
                module.fail_json(
                    msg="Timeout waiting for machine %s to get to state %s" % (
                        devide.id, state))

        changed = True
        machines.append(machine)

    return {
        'changed': changed,
        'machines': [_serialize_machine(machine) for machine in machines]
    }


def _generate_hostnames(template, count, start_index=1):
    """
    Returns an array of hostnames based on a template. If the template
    contains '%02d' or '%03d', the count is substituted in, otherwise
    we append '-%02d' at the end of the template.
    """
    # If the name has %02d or %03d somewhere in the host name, drop the
    # increment count in that location
    if '%02d' in template or '%03d' in template:
        str_formatted_name = template
    # Otherwise, default to name-01, name-02, onwards
    else:
        # str_formatted_name = "%s-%%02d" % template
        str_formatted_name = "%s-%%01d" % template

    end_index = count + start_index

    return [
        str_formatted_name % i
        for i in xrange(start_index, end_index)
        # for i in xrange(1, count + 1)
    ]


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str'),
            appliance=dict(type='str'),
            fixed_instance_size=dict(type='str'),
            count=dict(type='int', default=1),
            ssh_key=dict(type='raw', default=None),
            auto_increment=dict(type='bool', default=True),
            instance_ids=dict(type='list'),
            auth_token=dict(type='str'),
            datacenter=dict(
                choices=DATACENTERS,
                default='US'),
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
            module.exit_json(**remove_machine(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state in ('running', 'stopped'):
        try:
            module.exit_json(**startstop_machine(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('hostname',
                      'appliance',
                      'fixed_instance_size',
                      'datacenter'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new instance." % param)
        try:
            module.exit_json(**create_machine(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
