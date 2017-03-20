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
module: oneandone_roles
short_description: Configure 1&1 roles.
description:
     - Create, remove, update a role
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  state:
    description:
      - Define a role's state to create, remove, or update.
    required: false
    default: 'present'
    choices: [ "present", "absent", "update" ]
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - Role name.
    maxLength: 128
    required: true
  description:
    description:
      - Role description.
    required: false
  state:
    description:
      - Allows to enable or disable the role
    required: false

requirements:
     - "1and1"
     - "python >= 2.6"
author: Amel Ajdinovic (amel@stackpointcloud.com)
'''

HAS_ONEANDONE_SDK = True

try:
    import oneandone.client
except ImportError:
    HAS_ONEANDONE_SDK = False

ROLE_STATES = ['ACTIVE', 'DISABLE']


def _find_role(oneandone_conn, name):
    """
    Given a name, validates that the role exists
    whether it is a proper ID or a name.
    Returns the role if one was found, else None.
    """
    role = None
    roles = oneandone_conn.list_roles(per_page=1000)
    for _role in roles:
        if name in (_role['id'], _role['name']):
            role = _role
            break
    return role


def _wait_for_role_creation_completion(oneandone_conn, role, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the role info
        role = oneandone_conn.get_role(role['id'])

        if role['state'].lower() == 'active':
            return
        elif role['state'].lower() == 'failed':
            raise Exception('User creation ' +
                            ' failed for %s' % role['id'])
        elif role['state'].lower() in ('active',
                                       'enabled',
                                       'deploying',
                                       'configuring'):
            continue
        else:
            raise Exception(
                'Unknown role state %s' % role['state'])

    raise Exception(
        'Timed out waiting for role competion for %s' % role['id'])


def _modify_role_permissions(module, oneandone_conn, role_id,
                             servers, images, shared_storages, firewalls,
                             load_balancers, ips, private_networks, vpns,
                             monitoring_centers, monitoring_policies, backups,
                             logs, users, roles, usages, interactive_invoices):
    """
    """

    try:
        role = oneandone_conn.modify_permissions(role_id=role_id, servers=servers, images=images,
                                                 shared_storages=shared_storages, firewalls=firewalls,
                                                 load_balancers=load_balancers, ips=ips,
                                                 private_networks=private_networks, vpns=vpns,
                                                 monitoring_centers=monitoring_centers,
                                                 monitoring_policies=monitoring_policies, backups=backups, logs=logs,
                                                 users=users, roles=roles, usages=usages,
                                                 interactive_invoices=interactive_invoices)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def _add_users_to_role(module, oneandone_conn, role_id, users):
    try:
        role = oneandone_conn.add_users(role_id=role_id,
                                        users=users)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_users_from_role(module, oneandone_conn, role_id, users):
    role = None
    try:
        for user_id in users:
            role = oneandone_conn.remove_user(role_id=role_id,
                                              user_id=user_id)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def _clone_role(module, oneandone_conn, role_id, name):
    try:
        role = oneandone_conn.clone_role(role_id=role_id,
                                         name=name)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def update_role(module, oneandone_conn):
    """
    Update a user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    role_id = module.params.get('role')
    _name = module.params.get('name')
    _description = module.params.get('description')
    _state = module.params.get('state')
    _servers, = module.params.get('servers')
    _images = module.params.get('images')
    _shared_storages = module.params.get('shared_storages')
    _firewalls = module.params.get('firewalls')
    _load_balancers = module.params.get('load_balancers')
    _ips = module.params.get('ips')
    _private_networks = module.params.get('private_networks')
    _vpns = module.params.get('vpns')
    _monitoring_centers = module.params.get('monitoring_centers')
    _monitoring_policies = module.params.get('monitoring_policies')
    _backups = module.params.get('backups')
    _logs = module.params.get('logs')
    _users = module.params.get('users')
    _roles = module.params.get('roles')
    _usages = module.params.get('usages')
    _interactive_invoices = module.params.get('interactive_invoices')
    _add_users = module.params.get('add_users')
    _remove_users = module.params.get('remove_users')
    _role_clone_name = module.params.get('role_clone_name')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    role = _find_role(oneandone_conn, role_id)

    try:
        if _name or _description or _state:
            role = oneandone_conn.modify_role(
                role_id=role['id'],
                name=_name,
                description=_description,
                state=_state)

        if should_update_permissions(_servers, _images, _shared_storages, _firewalls,
                                     _load_balancers, _ips, _private_networks, _vpns,
                                     _monitoring_centers, _monitoring_policies, _backups,
                                     _logs, _users, _roles, _usages, _interactive_invoices):
            role = _modify_role_permissions(module=module,
                                            oneandone_conn=oneandone_conn,
                                            role_id=role['id'],
                                            servers=_servers,
                                            images=_images,
                                            shared_storages=_shared_storages,
                                            firewalls=_firewalls,
                                            load_balancers=_load_balancers,
                                            ips=_ips,
                                            private_networks=_private_networks,
                                            vpns=_vpns,
                                            monitoring_centers=_monitoring_centers,
                                            monitoring_policies=_monitoring_policies,
                                            backups=_backups,
                                            logs=_logs,
                                            users=_users,
                                            roles=_roles,
                                            usages=_usages,
                                            interactive_invoices=_interactive_invoices)

        if _add_users:
            role = _add_users_to_role(module=module,
                                      oneandone_conn=oneandone_conn,
                                      role_id=role['id'],
                                      users=_add_users)

        if _remove_users:
            role = _remove_users_from_role(module=module,
                                           oneandone_conn=oneandone_conn,
                                           role_id=role['id'],
                                           users=_remove_users)

        if _role_clone_name:
            role = _clone_role(module=module,
                               oneandone_conn=oneandone_conn,
                               role_id=role['id'],
                               name=_role_clone_name)

        if wait:
            _wait_for_role_creation_completion(
                oneandone_conn, role, wait_timeout)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def should_update_permissions(servers, images, shared_storages, firewalls,
                              load_balancers, ips, private_networks, vpns,
                              monitoring_centers, monitoring_policies, backups,
                              logs, users, roles, usages, interactive_invoices):
    """
    Returns: True if any of the arguments is not none
    """
    args = [servers, images, shared_storages, firewalls, load_balancers, ips, private_networks, vpns,
            monitoring_centers, monitoring_policies, backups, logs, users, roles, usages, interactive_invoices]

    if args.any():
        return True
    else:
        return False


def create_role(module, oneandone_conn):
    """
    Create a new role

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    name = module.params.get('name')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    try:
        role = oneandone_conn.create_role(name=name)

        if wait:
            _wait_for_role_creation_completion(
                oneandone_conn, role, wait_timeout)

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_role(module, oneandone_conn):
    """
    Delete a role

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    role_id = module.params.get('role')
    _role = _find_role(oneandone_conn, role_id)

    try:
        role = oneandone_conn.delete_role(_role['id'])

        return role
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str'),
            description=dict(type='str'),
            role_state=dict(
                choices=ROLE_STATES),
            role=dict(type='str'),
            servers=dict(type='str'),
            images=dict(type='str'),
            shared_storages=dict(type='str'),
            firewalls=dict(type='str'),
            load_balancers=dict(type='str'),
            ips=dict(type='str'),
            private_networks=dict(type='str'),
            vpns=dict(type='str'),
            monitoring_centers=dict(type='str'),
            monitoring_policies=dict(type='str'),
            backups=dict(type='str'),
            logs=dict(type='str'),
            users=dict(type='str'),
            roles=dict(type='str'),
            usages=dict(type='str'),
            interactive_invoices=dict(type='str'),
            add_users=dict(type='list', default=[]),
            remove_users=dict(type='list', default=[]),
            role_clone_name=dict(type='str'),
            auth_token=dict(type='str'),
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
            module.exit_json(**remove_role(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            module.exit_json(**update_role(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name', 'password'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new roles." % param)
        try:
            module.exit_json(**create_role(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
