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
module: oneandone_monitoring_policy
short_description: Configure 1&1 monitoring policy.
description:
     - Create, remove, update monitoring policies
       (and add/remove ports, processes, and servers).
version_added: "2.4"
options:
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - Monitoring policy name used with present state. Used as identifier (id or name) when used with absent state.
    maxLength: 128
    required: true
  monitoring_policy:
    description:
      - The identifier (id or name) of the monitoring policy used with update state.
    required: true
  agent:
    description:
      - Set true for using agent.
    required: true
  email:
    description:
      - User's email.
    maxLength: 128
    required: true
  description:
    description:
      - Monitoring policy description.
    maxLength: 256
    required: false
  thresholds:
    description:
      - Monitoring policy thresholds.
    required: true
    suboptions:
      cpu:
        description:
          - Consumption limits of CPU.
        required: true
        suboptions:
          warning:
            description:
              - Set limits for warning.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                minimum: 1
                maximum: 95
                required: true
          critical:
            description:
              - Set limits for critical case.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                maximum: 100
                required: true
      ram:
        description:
          - Consumption limits of RAM.
        required: true
        suboptions:
          warning:
            description:
              - Set limits for warning.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                minimum: 1
                maximum: 95
                required: true
          critical:
            description:
              - Set limits for critical case.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                maximum: 100
                required: true
      disk:
        description:
          - Consumption limits of hard disk.
        required: true
        suboptions:
          warning:
            description:
              - Set limits for warning.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                minimum: 1
                maximum: 95
                required: true
          critical:
            description:
              - Set limits for critical case.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (%).
                maximum: 100
                required: true
      internal_ping:
        description:
          - Response limits of internal ping.
        required: true
        suboptions:
          warning:
            description:
              - Set limits for warning.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (ms).
                required: true
          critical:
            description:
              - Set limits for critical case.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (ms).
                maximum: 100
                required: true
      transfer:
        description:
          - Consumption limits for transfer.
        required: true
        suboptions:
          warning:
            description:
              - Set limits for warning.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (kbps).
                minimum: 1
                required: true
          critical:
            description:
              - Set limits for critical case.
            required: true
            suboptions:
              alert:
                description:
                  - Enable alert.
                required: true
              value:
                description:
                  - Advise when this value is exceeded (kbps).
                maximum: 2000
                required: true
  ports:
    description:
      - Array of ports that will be monitoring.
    required: true
    suboptions:
      protocol:
        description:
          - Internet protocol.
        choices: [ "TCP", "UDP" ]
        required: true
      port:
        description:
          - Port number.
        minimum: 1
        maximum: 65535
        required: true
      alert_if:
        description:
          - Case of alert.
        choices: [ "RESPONDING", "NOT_RESPONDING" ]
        required: true
      email_notification:
        description:
          - Set true for sending e-mail notifications.
        required: true
  processes:
    description:
      - Array of processes that will be monitoring.
    required: true
    suboptions:
      process:
        description:
          - Name of the process.
        maxLength: 50
        required: true
      alert_if:
        description:
          - Case of alert.
        choices: [ "RUNNING", "NOT_RUNNING" ]
        required: true

requirements:
     - "1and1"
     - "python >= 2.6"
author: "Amel Ajdinovic (@aajdinov), Ethan Devenport (@edevenport)"
'''

EXAMPLES = '''

# Provisioning example. Create and destroy a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    name: ansible monitoring policy
    description: Testing creation of a monitoring policy with ansible
    email: your@emailaddress.com
    agent: true
    thresholds:
     -
       cpu:
         warning:
           value: 80
           alert: false
         critical:
           value: 92
           alert: false
     -
       ram:
         warning:
           value: 80
           alert: false
         critical:
           value: 90
           alert: false
     -
       disk:
         warning:
           value: 80
           alert: false
         critical:
           value: 90
           alert: false
     -
       internal_ping:
         warning:
           value: 50
           alert: false
         critical:
           value: 100
           alert: false
     -
       transfer:
         warning:
           value: 1000
           alert: false
         critical:
           value: 2000
           alert: false
    ports:
     -
       protocol: TCP
       port: 22
       alert_if: RESPONDING
       email_notification: false
    processes:
     -
       process: test
       alert_if: NOT_RUNNING
       email_notification: false
    wait: true

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    state: absent
    name: ansible monitoring policy

# Update a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy
    name: ansible monitoring policy updated
    description: Testing creation of a monitoring policy with ansible updated
    email: another@emailaddress.com
    thresholds:
     -
       cpu:
         warning:
           value: 70
           alert: false
         critical:
           value: 90
           alert: false
     -
       ram:
         warning:
           value: 70
           alert: false
         critical:
           value: 80
           alert: false
     -
       disk:
         warning:
           value: 70
           alert: false
         critical:
           value: 80
           alert: false
     -
       internal_ping:
         warning:
           value: 60
           alert: false
         critical:
           value: 90
           alert: false
     -
       transfer:
         warning:
           value: 900
           alert: false
         critical:
           value: 1900
           alert: false
    wait: true
    state: update

# Add a port to a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    add_ports:
     -
       protocol: TCP
       port: 33
       alert_if: RESPONDING
       email_notification: false
    wait: true
    state: update

# Update existing ports of a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    update_ports:
     -
       id: existing_port_id
       protocol: TCP
       port: 34
       alert_if: RESPONDING
       email_notification: false
     -
       id: existing_port_id
       protocol: TCP
       port: 23
       alert_if: RESPONDING
       email_notification: false
    wait: true
    state: update

# Remove a port from a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    remove_ports:
     - port_id
    state: update

# Add a process to a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    add_processes:
     -
       process: test_2
       alert_if: NOT_RUNNING
       email_notification: false
    wait: true
    state: update

# Update existing processes of a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    update_processes:
     -
       id: process_id
       process: test_1
       alert_if: NOT_RUNNING
       email_notification: false
     -
       id: process_id
       process: test_3
       alert_if: NOT_RUNNING
       email_notification: false
    wait: true
    state: update

# Remove a process from a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    remove_processes:
     - process_id
    wait: true
    state: update

# Add server to a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    add_servers:
     - server id or name
    wait: true
    state: update

# Remove server from a monitoring policy.

- oneandone_moitoring_policy:
    auth_token: oneandone_private_api_key
    monitoring_policy: ansible monitoring policy updated
    remove_servers:
     - server01
    wait: true
    state: update
'''

import os
import time
from ansible.module_utils.basic import AnsibleModule

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False


def _wait_for_monitoring_policy_creation_completion(oneandone_conn, monitoring_policy, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the monitoring policy info
        monitoring_policy = oneandone_conn.get_monitoring_policy(monitoring_policy['id'])

        if monitoring_policy['state'].lower() == 'active':
            return
        elif monitoring_policy['state'].lower() == 'failed':
            raise Exception('Monitoring policy creation ' +
                            ' failed for %s' % monitoring_policy['id'])
        elif monitoring_policy['state'].lower() in ('enabled',
                                                    'deploying',
                                                    'configuring'):
            continue
        else:
            raise Exception(
                'Unknown monitoring policy state %s' % monitoring_policy['state'])

    raise Exception(
        'Timed out waiting for monitoring policy competion for %s' % monitoring_policy['id'])


def _find_monitoring_policy(oneandone_conn, monitoring_policy):
    """
    Given a name, validates that the monitoring policy exists
    whether it is a proper ID or a name.
    Returns the monitoring_policy if one was found, else None.
    """
    for _monitoring_policy in oneandone_conn.list_monitoring_policies(per_page=1000):
        if monitoring_policy in (_monitoring_policy['id'], _monitoring_policy['name']):
            return _monitoring_policy


def _find_machine(oneandone_conn, instance):
    """
    Validates that the machine exists whether by ID or name.
    Returns the machine id if found.
    """
    for _machine in oneandone_conn.list_servers(per_page=1000):
        if instance in (_machine['id'], _machine['name']):
            return _machine['id']


def _add_ports(module, oneandone_conn, monitoring_policy_id, ports):
    """
    Adds new ports to a monitoring policy.
    """
    try:
        monitoring_policy_ports = []

        for _port in ports:
            monitoring_policy_port = oneandone.client.Port(
                protocol=_port['protocol'],
                port=_port['port'],
                alert_if=_port['alert_if'],
                email_notification=_port['email_notification']
            )
            monitoring_policy_ports.append(monitoring_policy_port)

        monitoring_policy = oneandone_conn.add_port(
            monitoring_policy_id=monitoring_policy_id,
            ports=monitoring_policy_ports)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _delete_monitoring_policy_port(module, oneandone_conn, monitoring_policy_id, port_id):
    """
    Removes a port from a monitoring policy.
    """
    try:
        monitoring_policy = oneandone_conn.delete_monitoring_policy_port(
            monitoring_policy_id=monitoring_policy_id,
            port_id=port_id)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _modify_port(module, oneandone_conn, monitoring_policy_id, port_id, port):
    """
    Modifies a monitoring policy port.
    """
    try:
        monitoring_policy_port = oneandone.client.Port(
            protocol=port['protocol'],
            port=port['port'],
            alert_if=port['alert_if'],
            email_notification=port['email_notification']
        )

        monitoring_policy = oneandone_conn.modify_port(
            monitoring_policy_id=monitoring_policy_id,
            port_id=port_id,
            port=monitoring_policy_port)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _add_processes(module, oneandone_conn, monitoring_policy_id, processes):
    """
    Adds new processes to a monitoring policy.
    """
    try:
        monitoring_policy_processes = []

        for _process in processes:
            monitoring_policy_process = oneandone.client.Process(
                process=_process['process'],
                alert_if=_process['alert_if'],
                email_notification=_process['email_notification']
            )
            monitoring_policy_processes.append(monitoring_policy_process)

        monitoring_policy = oneandone_conn.add_process(
            monitoring_policy_id=monitoring_policy_id,
            processes=monitoring_policy_processes)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _delete_monitoring_policy_process(module, oneandone_conn, monitoring_policy_id, process_id):
    """
    Removes a process from a monitoring policy.
    """
    try:
        monitoring_policy = oneandone_conn.delete_monitoring_policy_process(
            monitoring_policy_id=monitoring_policy_id,
            process_id=process_id)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _modify_process(module, oneandone_conn, monitoring_policy_id, process_id, process):
    """
    Modifies a monitoring policy process.
    """
    try:
        monitoring_policy_process = oneandone.client.Process(
            process=process['process'],
            alert_if=process['alert_if'],
            email_notification=process['email_notification']
        )

        monitoring_policy = oneandone_conn.modify_process(
            monitoring_policy_id=monitoring_policy_id,
            process_id=process_id,
            process=monitoring_policy_process)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _attach_monitoring_policy_server(module, oneandone_conn, monitoring_policy_id, servers):
    """
    Attaches servers to a monitoring policy.
    """
    try:
        attach_servers = []

        for _server_id in servers:
            server_id = _find_machine(oneandone_conn, _server_id)
            attach_server = oneandone.client.AttachServer(
                server_id=server_id
            )
            attach_servers.append(attach_server)

        monitoring_policy = oneandone_conn.attach_monitoring_policy_server(
            monitoring_policy_id=monitoring_policy_id,
            servers=attach_servers)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def _detach_monitoring_policy_server(module, oneandone_conn, monitoring_policy_id, server_id):
    """
    Detaches a server from a monitoring policy.
    """
    try:
        monitoring_policy = oneandone_conn.detach_monitoring_policy_server(
            monitoring_policy_id=monitoring_policy_id,
            server_id=server_id)
        return monitoring_policy
    except Exception as ex:
        module.fail_json(msg=str(ex))


def update_monitoring_policy(module, oneandone_conn):
    """
    Updates a monitoring_policy based on input arguments.
    Monitoring policy ports, processes and servers can be added/removed to/from
    a monitoring policy. Monitoring policy name, description, email,
    thresholds for cpu, ram, disk, transfer and internal_ping
    can be updated as well.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        monitoring_policy_id = module.params.get('monitoring_policy')
        name = module.params.get('name')
        description = module.params.get('description')
        email = module.params.get('email')
        thresholds = module.params.get('thresholds')
        add_ports = module.params.get('add_ports')
        update_ports = module.params.get('update_ports')
        remove_ports = module.params.get('remove_ports')
        add_processes = module.params.get('add_processes')
        update_processes = module.params.get('update_processes')
        remove_processes = module.params.get('remove_processes')
        add_servers = module.params.get('add_servers')
        remove_servers = module.params.get('remove_servers')

        changed = False

        monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy_id)

        _monitoring_policy = oneandone.client.MonitoringPolicy(
            name=name,
            description=description,
            email=email
        )

        _thresholds = None

        if thresholds:
            threshold_entities = ['cpu', 'ram', 'disk', 'internal_ping', 'transfer']

            _thresholds = []
            for treshold in thresholds:
                key = treshold.keys()[0]
                if key in threshold_entities:
                    _threshold = oneandone.client.Threshold(
                        entity=key,
                        warning_value=treshold[key]['warning']['value'],
                        warning_alert=str(treshold[key]['warning']['alert']).lower(),
                        critical_value=treshold[key]['critical']['value'],
                        critical_alert=str(treshold[key]['critical']['alert']).lower())
                    _thresholds.append(_threshold)

        if name or description or email or thresholds:
            monitoring_policy = oneandone_conn.modify_monitoring_policy(
                monitoring_policy_id=monitoring_policy['id'],
                monitoring_policy=_monitoring_policy,
                thresholds=_thresholds)
            changed = True

        if add_ports:
            monitoring_policy = _add_ports(module, oneandone_conn, monitoring_policy['id'], add_ports)
            changed = True

        if update_ports:
            for update_port in update_ports:
                _modify_port(module,
                             oneandone_conn,
                             monitoring_policy['id'],
                             update_port['id'],
                             update_port)
            monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy['id'])
            changed = True

        if remove_ports:
            for port_id in remove_ports:
                _delete_monitoring_policy_port(module,
                                               oneandone_conn,
                                               monitoring_policy['id'],
                                               port_id)
            monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy['id'])
            changed = True

        if add_processes:
            monitoring_policy = _add_processes(module, oneandone_conn, monitoring_policy['id'], add_processes)
            changed = True

        if update_processes:
            for update_process in update_processes:
                _modify_process(module,
                                oneandone_conn,
                                monitoring_policy['id'],
                                update_process['id'],
                                update_process)
            monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy['id'])
            changed = True

        if remove_processes:
            for process_id in remove_processes:
                _delete_monitoring_policy_process(module,
                                                  oneandone_conn,
                                                  monitoring_policy['id'],
                                                  process_id)
            monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy['id'])
            changed = True

        if add_servers:
            monitoring_policy = _attach_monitoring_policy_server(module,
                                                                 oneandone_conn,
                                                                 monitoring_policy['id'],
                                                                 add_servers)
            changed = True

        if remove_servers:
            for _server_id in remove_servers:
                server_id = _find_machine(oneandone_conn, _server_id)
                _detach_monitoring_policy_server(module,
                                                 oneandone_conn,
                                                 monitoring_policy['id'],
                                                 server_id)
            monitoring_policy = _find_monitoring_policy(oneandone_conn, monitoring_policy['id'])
            changed = True

        return (changed, monitoring_policy)
    except Exception as ex:
        module.fail_json(msg=str(ex))


def create_monitoring_policy(module, oneandone_conn):
    """
    Creates a new monitoring policy.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        name = module.params.get('name')
        description = module.params.get('description')
        email = module.params.get('email')
        agent = module.params.get('agent')
        thresholds = module.params.get('thresholds')
        ports = module.params.get('ports')
        processes = module.params.get('processes')
        wait = module.params.get('wait')
        wait_timeout = module.params.get('wait_timeout')

        _monitoring_policy = oneandone.client.MonitoringPolicy(name,
                                                               description,
                                                               email,
                                                               agent, )

        _monitoring_policy.specs['agent'] = str(_monitoring_policy.specs['agent']).lower()

        threshold_entities = ['cpu', 'ram', 'disk', 'internal_ping', 'transfer']

        _thresholds = []
        for treshold in thresholds:
            key = treshold.keys()[0]
            if key in threshold_entities:
                _threshold = oneandone.client.Threshold(
                    entity=key,
                    warning_value=treshold[key]['warning']['value'],
                    warning_alert=str(treshold[key]['warning']['alert']).lower(),
                    critical_value=treshold[key]['critical']['value'],
                    critical_alert=str(treshold[key]['critical']['alert']).lower())
                _thresholds.append(_threshold)

        _ports = []
        for port in ports:
            _port = oneandone.client.Port(
                protocol=port['protocol'],
                port=port['port'],
                alert_if=port['alert_if'],
                email_notification=str(port['email_notification']).lower())
            _ports.append(_port)

        _processes = []
        for process in processes:
            _process = oneandone.client.Process(
                process=process['process'],
                alert_if=process['alert_if'],
                email_notification=str(process['email_notification']).lower())
            _processes.append(_process)

        monitoring_policy = oneandone_conn.create_monitoring_policy(
            monitoring_policy=_monitoring_policy,
            thresholds=_thresholds,
            ports=_ports,
            processes=_processes
        )

        if wait:
            _wait_for_monitoring_policy_creation_completion(
                oneandone_conn,
                monitoring_policy,
                wait_timeout)

        changed = True if monitoring_policy else False

        return (changed, monitoring_policy)
    except Exception as ex:
        module.fail_json(msg=str(ex))


def remove_monitoring_policy(module, oneandone_conn):
    """
    Removes a monitoring policy.

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    try:
        mp_id = module.params.get('name')
        monitoring_policy = _find_monitoring_policy(oneandone_conn, mp_id)
        monitoring_policy = oneandone_conn.delete_monitoring_policy(monitoring_policy['id'])

        changed = True if monitoring_policy else False

        return (changed, {
            'id': monitoring_policy['id'],
            'name': monitoring_policy['name']
        })
    except Exception as ex:
        module.fail_json(msg=str(ex))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN'),
                no_log=True),
            name=dict(type='str'),
            monitoring_policy_id=dict(type='str'),
            agent=dict(type='str'),
            email=dict(type='str'),
            description=dict(type='str'),
            thresholds=dict(type='list', default=[]),
            ports=dict(type='list', default=[]),
            processes=dict(type='list', default=[]),
            add_ports=dict(type='list', default=[]),
            update_ports=dict(type='list', default=[]),
            remove_ports=dict(type='list', default=[]),
            add_processes=dict(type='list', default=[]),
            update_processes=dict(type='list', default=[]),
            remove_processes=dict(type='list', default=[]),
            add_servers=dict(type='list', default=[]),
            remove_servers=dict(type='list', default=[]),
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
        if not module.params.get('name'):
            module.fail_json(
                msg="'name' parameter is required to delete a monitoring policy.")
        try:
            (changed, monitoring_policy) = remove_monitoring_policy(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))
    elif state == 'update':
        if not module.params.get('monitoring_policy'):
            module.fail_json(
                msg="'monitoring_policy' parameter is required to update a monitoring policy.")
        try:
            (changed, monitoring_policy) = update_monitoring_policy(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))

    elif state == 'present':
        for param in ('name', 'agent', 'email', 'thresholds', 'ports', 'processes'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for a new monitoring policy." % param)
        try:
            (changed, monitoring_policy) = create_monitoring_policy(module, oneandone_conn)
        except Exception as ex:
            module.fail_json(msg=str(ex))

    module.exit_json(changed=changed, monitoring_policy=monitoring_policy)


if __name__ == '__main__':
    main()
