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
      - Authenticating API token provided by 1&1. Overrides the
        ONEANDONE_AUTH_TOKEN environement variable.
    required: true
  hostname:
    description:
      - The hostname or ID of the machine. Only used when state is 'present'.
    required: true when state is 'present', false otherwise.
  description:
    description:
      - The description of the machine.
    required: false
  appliance:
    description:
      - The operating system name or ID for the machine.
    required: true for 'present' state, false otherwise
  fixed_instance_size:
    description:
      - The instance size name or ID of the machine.
    required: true for 'present' state, false otherwise
    choices: [ "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL" ]
  datacenter:
    description:
      - The datacenter location.
    required: false
    default: US
    choices: [ "US", "ES", "DE", "GB" ]
  private_network:
    description:
      - The private network name or ID of the machine.
    required: false
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

author:
  - Amel Ajdinovic (@aajdinov)
  - Ethan Devenport (@edevenport)
'''

EXAMPLES = '''

# Provisioning example. Creates three servers and enumerate their names.

- oneandone:
    auth_token: oneandone_private_api_key
    hostname: node%02d
    fixed_instance_size: XL
    datacenter: US
    appliance: C5A349786169F140BCBC335675014C08
    auto_increment: true
    count: 3

# Create three machines, passing in an ssh_key.

- oneandone:
    auth_token: oneandone_private_api_key
    hostname: node%02d
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
      - 'node01'
      - 'node02'
      - 'node03'

# Starting Machines.

- oneandone:
    auth_token: oneandone_private_api_key
    state: running
    instance_ids:
      - 'node01'
      - 'node02'
      - 'node03'

# Stopping Machines

- oneandone:
    auth_token: oneandone_private_api_key
    state: stopped
    instance_ids:
      - 'node01'
      - 'node02'
      - 'node03'
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


def _find_datacenter(oneandone_conn, datacenter):
    """
    Validates the datacenter exists by ID or country code.
    Returns the datacenter ID.
    """
    for _datacenter in oneandone_conn.list_datacenters():
        if datacenter in (_datacenter['id'], _datacenter['country_code']):
            return _datacenter['id']


def _find_fixed_instance_size(oneandone_conn, fixed_instance_size):
    """
    Validates the fixed instance size exists by ID or name.
    Return the instance size ID.
    """
    for _fixed_instance_size in oneandone_conn.fixed_server_flavors():
        if fixed_instance_size in (_fixed_instance_size['id'],
                                   _fixed_instance_size['name']):
            return _fixed_instance_size['id']


def _find_appliance(oneandone_conn, appliance):
    """
    Validates the appliance exists by ID or name.
    Return the appliance ID.
    """
    for _appliance in oneandone_conn.list_appliances(q='IMAGE'):
        if appliance in (_appliance['id'], _appliance['name']):
            return _appliance['id']


def _find_private_network(oneandone_conn, private_network):
    """
    Validates the private network exists by ID or name.
    Return the private network ID.
    """
    for _private_network in oneandone_conn.list_private_networks():
        if private_network in (_private_network['name'],
                               _private_network['id']):
            return _private_network['id']


def _find_machine(oneandone_conn, instance):
    """
    Validates that the machine exists whether by ID or name.
    Returns the machine if one was found.
    """
    for _machine in oneandone_conn.list_servers(per_page=1000):
        if instance in (_machine['id'], _machine['name']):
            return _machine


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


def _create_machine(module, oneandone_conn, hostname, description,
                    fixed_instance_size_id, vcore, cores_per_processor, ram, hdds,
                    datacenter_id, appliance_id, ssh_key, private_network_id, wait, wait_timeout):

    try:
        machine = oneandone_conn.create_server(
            oneandone.client.Server(
                name=hostname,
                description=description,
                fixed_instance_size_id=fixed_instance_size_id,
                vcore=vcore,
                cores_per_processor=cores_per_processor,
                ram=ram,
                appliance_id=appliance_id,
                datacenter_id=datacenter_id,
                rsa_key=ssh_key,
                private_network_id=private_network_id), hdds)

        if wait:
            _wait_for_machine_creation_completion(
                oneandone_conn, machine, wait_timeout)
            machine = oneandone_conn.get_server(machine['id'])  # refresh

        return machine
    except Exception as e:
        module.fail_json(msg=str(e))


def _insert_network_data(machine):
    for addr_data in machine['ips']:
        if addr_data['type'] == 'IPV6':
            machine['public_ipv6'] = addr_data['ip']
        elif addr_data['type'] == 'IPV4':
            machine['public_ipv4'] = addr_data['ip']
    return machine


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
    description = module.params.get('description')
    auto_increment = module.params.get('auto_increment')
    count = module.params.get('count')
    fixed_instance_size = module.params.get('fixed_instance_size')
    vcore = module.params.get('vcore')
    cores_per_processor = module.params.get('cores_per_processor')
    ram = module.params.get('ram')
    hdds = module.params.get('hdds')
    datacenter = module.params.get('datacenter')
    appliance = module.params.get('appliance')
    ssh_key = module.params.get('ssh_key')
    private_network = module.params.get('private_network')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    private_network_id = None

    datacenter_id = _find_datacenter(oneandone_conn, datacenter)
    if datacenter_id is None:
        module.fail_json(
            msg='datacenter %s not found.' % datacenter)

    if fixed_instance_size:
        fixed_instance_size_id = _find_fixed_instance_size(
            oneandone_conn,
            fixed_instance_size)
        if fixed_instance_size_id is None:
            module.fail_json(
                msg='fixed_instance_size %s not found.' % fixed_instance_size)

    appliance_id = _find_appliance(oneandone_conn, appliance)
    if appliance_id is None:
        module.fail_json(
            msg='datacenter %s not found.' % appliance)

    if private_network:
        private_network_id = _find_private_network(
            oneandone_conn,
            private_network)
        if private_network_id is None:
            module.fail_json(
                msg='private network %s not found.' % private_network)

    if auto_increment:
        hostnames = _auto_increment_hostname(count, hostname)
        descriptions = _auto_increment_description(count, description)
    else:
        hostnames = [hostname] * count
        descriptions = [description] * count

    machines = []
    for index, name in enumerate(hostnames):
        machines.append(
            _create_machine(
                module=module,
                oneandone_conn=oneandone_conn,
                hostname=name,
                description=descriptions[index],
                fixed_instance_size_id=fixed_instance_size_id,
                vcore=vcore,
                cores_per_processor=cores_per_processor,
                ram=ram,
                hdds=hdds,
                datacenter_id=datacenter_id,
                appliance_id=appliance_id,
                ssh_key=ssh_key,
                private_network_id=private_network_id,
                wait=wait,
                wait_timeout=wait_timeout))

    changed = True if machines else False
    machines = [_insert_network_data(machine) for machine in machines]

    return (changed, machines)


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
    for instance in instance_ids:
        machine = _find_machine(oneandone_conn, instance)
        if machine is None:
            continue

        try:
            oneandone_conn.delete_server(server_id=machine['id'])
            removed_machines.append(machine)
        except Exception as e:
            module.fail_json(
                msg="failed to terminate the machine: %s" % str(e))

    changed = True if removed_machines else False
    machines = [{
        'id': machine['id'],
        'hostname': machine['name'],
    } for machine in removed_machines]

    return (changed, machines)


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
                machine_state = machine['status']['state']
                if state == 'stopped' and machine_state == 'POWERED_OFF':
                    operation_completed = True
                    break
                if state == 'running' and machine_state == 'POWERED_ON':
                    operation_completed = True
                    break
            if not operation_completed:
                module.fail_json(
                    msg="Timeout waiting for machine %s to get to state %s" % (
                        instance_id, state))

        changed = True
        machines.append(machine)

    machines = [_insert_network_data(machine) for machine in machines]

    return (changed, machines)


def _auto_increment_hostname(count, hostname):
    """
    Allow a custom incremental count in the hostname when defined with the
    string formatting (%) operator. Otherwise, increment using name-01,
    name-02, name-03, and so forth.
    """
    if '%' not in hostname:
        hostname = "%s-%%01d" % hostname

    return [
        hostname % i
        for i in xrange(1, count + 1)
    ]


def _auto_increment_description(count, description):
    """
    Allow the incremental count in the description when defined with the
    string formatting (%) operator. Otherwise, repeat the same description.
    """
    if '%' in description:
        return [
            description % i
            for i in xrange(1, count + 1)
        ]
    else:
        return [description] * count


def _validate_custom_hardware_params(module):
    for param in ('vcore',
                  'cores_per_processor',
                  'ram',
                  'hdds'):
        if not module.params.get(param):
            return False
    return True


def _validate_hardware_params(module):
    if bool(module.params.get('fixed_instance_size')) ^ bool(_validate_custom_hardware_params(module)):
        return True
    return False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            hostname=dict(type='str'),
            description=dict(type='str'),
            appliance=dict(type='str'),
            fixed_instance_size=dict(type='str'),
            vcore=dict(type='int'),
            cores_per_processor=dict(type='int'),
            ram=dict(type='float'),
            hdds=dict(type='list'),
            count=dict(type='int', default=1),
            ssh_key=dict(type='raw', default=None),
            auto_increment=dict(type='bool', default=True),
            instance_ids=dict(type='list'),
            datacenter=dict(
                choices=DATACENTERS,
                default='US'),
            private_network=dict(type='str'),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            state=dict(type='str', default='present'),
        )
    )

    if not HAS_ONEANDONE_SDK:
        module.fail_json(msg='1and1 required for this module')

    if not module.params.get('auth_token'):
        module.fail_json(
            msg='The "auth_token" parameter or ' +
            'ONEANDONE_AUTH_TOKEN environment variable is required.')

    oneandone_conn = oneandone.client.OneAndOneService(
        api_token=module.params.get('auth_token'))

    state = module.params.get('state')

    if state == 'absent':
        try:
            (changed, machines) = remove_machine(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state in ('running', 'stopped'):
        try:
            (changed, machines) = startstop_machine(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        if not _validate_hardware_params(module):
            module.fail_json("Either fixed_size_instance parameter or full custom hardware specification parameters"
                             " must be provided (mutually exclusive).")
        for param in ('hostname',
                      'appliance',
                      'datacenter'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new instance." % param)
        try:
            (changed, machines) = create_machine(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=changed, machines=machines)


from ansible.module_utils.basic import *

main()
