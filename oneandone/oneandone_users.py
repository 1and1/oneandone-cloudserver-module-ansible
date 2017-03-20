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
module: oneandone_users
short_description: Configure 1&1 users.
description:
     - Create, remove, update a user
       This module has a dependency on 1and1 >= 1.0
version_added: "2.1"
options:
  state:
    description:
      - Define a user's state to create, remove, or update.
    required: false
    default: 'present'
    choices: [ "present", "absent", "update" ]
  auth_token:
    description:
      - Authenticating API token provided by 1&1.
    required: true
  name:
    description:
      - User's name.
    maxLength: 30
    required: true
  password:
    description:
      - User's password. Pass must contain at least 8 characters using uppercase letters, numbers,
        and other special symbols.
  description:
    description:
      - User description.
  email:
    description:
      - User's email

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

USER_STATES = ['ACTIVE', 'DISABLED']


def _find_user(oneandone_conn, name):
    """
    Given a name, validates that the user exists
    whether it is a proper ID or a name.
    Returns the user if one was found, else None.
    """
    user = None
    users = oneandone_conn.list_users(per_page=1000)
    for _user in users:
        if name in (_user['id'], _user['name']):
            user = _user
            break
    return user


def _wait_for_user_creation_completion(oneandone_conn, user, wait_timeout):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)

        # Refresh the user info
        user = oneandone_conn.get_user(user['id'])

        if user['state'].lower() == 'active':
            return
        elif user['state'].lower() == 'failed':
            raise Exception('User creation ' +
                            ' failed for %s' % user['id'])
        elif user['state'].lower() in ('active',
                                       'enabled',
                                       'deploying',
                                       'configuring'):
            continue
        else:
            raise Exception(
                'Unknown user state %s' % user['state'])

    raise Exception(
        'Timed out waiting for user competion for %s' % user['id'])


def _modify_user_api(module, oneandone_conn, user_id, active):
    """
    """

    try:
        user = oneandone_conn.modify_user_api(user_id=user_id, active=active)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def _change_api_key(module, oneandone_conn, user_id):
    """
    """

    try:
        user = oneandone_conn.change_api_key(user_id=user_id)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def _add_user_ip(module, oneandone_conn, user_id, user_ips):
    """
    """

    try:
        user = oneandone_conn.add_user_ip(
            user_id=user_id,
            user_ips=user_ips)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def _remove_user_ip(module, oneandone_conn, user_id, ip):
    """
    """

    try:
        user = oneandone_conn.remove_user_ip(
            user_id=user_id,
            ip=ip)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def update_user(module, oneandone_conn):
    """
    Update a user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    user_id = module.params.get('user')
    _description = module.params.get('description')
    _email = module.params.get('email')
    _password = module.params.get('password')
    _state = module.params.get('state')
    _user_ips = module.params.get('user_ips')
    _ip = module.params.get('remove_ip')
    _active = module.params.get('active')
    _key = module.params.get('change_api_key')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    user = _find_user(oneandone_conn, user_id)

    try:
        if _description or _email or _password or _state:
            user = oneandone_conn.modify_user(
                user_id=user['id'],
                description=_description,
                email=_email,
                password=_password,
                state=_state)

        if _user_ips:
            user = _add_user_ip(module=module,
                                oneandone_conn=oneandone_conn,
                                user_id=user['id'],
                                user_ips=_user_ips)

        if _ip:
            user = _remove_user_ip(module=module,
                                   oneandone_conn=oneandone_conn,
                                   user_id=user['id'],
                                   ip=_ip)

        if _active:
            user = _modify_user_api(module=module,
                                    oneandone_conn=oneandone_conn,
                                    user_id=user['id'],
                                    active=_active)

        if _key and _key==True:
            user = _change_api_key(module=module,
                                   oneandone_conn=oneandone_conn,
                                   user_id=user['id'])

        if wait:
            _wait_for_user_creation_completion(
                oneandone_conn, user, wait_timeout)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def create_user(module, oneandone_conn):
    """
    Create a new user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    name = module.params.get('name')
    description = module.params.get('description')
    password = module.params.get('password')
    email = module.params.get('email')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    try:
        user = oneandone_conn.create_user(
            name=name,
            password=password,
            email=email,
            description=description)

        if wait:
            _wait_for_user_creation_completion(
                oneandone_conn, user, wait_timeout)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_user(module, oneandone_conn):
    """
    Delete a new user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    user_id = module.params.get('user')
    _user = _find_user(oneandone_conn, user_id)

    try:
        user = oneandone_conn.delete_user(_user['id'])

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str'),
            description=dict(type='str'),
            password=dict(type='str'),
            email=dict(type='str'),
            active=dict(type='str'),
            user_ips=dict(type='list', default=[]),
            remove_ip=dict(type='str'),
            change_api_key=dict(type='bool', default=False),
            auth_token=dict(type='str'),
            user_state=dict(
                choices=USER_STATES),
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
            module.exit_json(**remove_user(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        try:
            module.exit_json(**update_user(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name', 'password'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new users." % param)
        try:
            module.exit_json(**create_user(module, oneandone_conn))
        except Exception as e:
            module.fail_json(msg=str(e))


from ansible.module_utils.basic import *

main()
