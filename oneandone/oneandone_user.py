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
module: oneandone_user
short_description: Configure 1&1 users.
description:
     - Create, remove, update a user
       This module has a dependency on 1and1 >= 1.0
version_added: "2.2"
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
  api_url:
    description:
      - Custom API URL. Overrides the
        ONEANDONE_API_URL environement variable.
    required: false  
  name:
    description:
      - User's name used with present state. Used as identifier (id or name) when used with absent state.
    maxLength: 30
    required: true
  user:
    description:
      - The identifier (id or name) of the user - used with update state.
    required: true
  user:
    description:
      - The identifier (id or name) of the user - used with update state.
    required: true
  password:
    description:
      - User's password. Pass must contain at least 8 characters using
        uppercase letters, numbers, and other special symbols.
  description:
    description:
      - User description.
  email:
    description:
      - User's email
  user_state:
    description:
      - Allows to enable or disable users
    choices: [ "ACTIVE", "DISABLE" ]
  active:
    description:
      - Set true for enabling API
  user_ips:
    description:
      - Array of new IPs from which access to API will be available.
  remove_ip:
    description:
      - Deletes an IP and forbides API access for it.
  change_api_key:
    description:
      - Changes the API key.
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

# Create a user.

- oneandone_user:
    auth_token: oneandone_private_api_key
    name: ansible_user
    description: Create a user with ansible
    password: desired password
    email: email@address.com

# Update a user.

- oneandone_user:
    auth_token: oneandone_private_api_key
    user: ansible_user
    description: Updated a user with ansible
    state: update


# Delete a user

- oneandone_user:
    auth_token: oneandone_private_api_key
    name: ansible_user
    state: absent

'''

EXAMPLES = '''

# Create a user.

- oneandone_user:
    auth_token: oneandone_private_api_key
    name: ansible_user
    description: Create a user with ansible
    password: desired password
    email: email@address.com

# Update a user.

- oneandone_user:
    auth_token: oneandone_private_api_key
    user: ansible_user
    description: Updated a user with ansible
    state: update


# Delete a user

- oneandone_user:
    auth_token: oneandone_private_api_key
    name: ansible_user
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

USER_STATES = ['ACTIVE', 'DISABLE']


def _find_user(oneandone_conn, user):
    """
    Validates that the user exists by ID or a name.
    Returns the user if one was found.
    """
    for _user in oneandone_conn.list_users(per_page=1000):
        if user in (_user['id'], _user['name']):
            return _user


def _wait_for_user_creation_completion(oneandone_conn, user_id, wait_timeout, wait_interval):
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(wait_interval)

        # Refresh the user info
        user = oneandone_conn.get_user(user_id)

        if user['state'].lower() == 'active':
            return
        elif user['state'].lower() == 'failed':
            raise Exception('User creation ' +
                            ' failed for %s' % user['id'])
        elif user['state'].lower() in ('enabled',
                                       'deploying',
                                       'configuring'):
            continue
        else:
            raise Exception(
                'Unknown user state %s' % user['state'])

    raise Exception(
        'Timed out waiting for user competion for %s' % user_id)


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


def _remove_user_ip(module, oneandone_conn, user_id, user_ip):
    """
    """

    try:
        user = oneandone_conn.remove_user_ip(
            user_id=user_id,
            ip=user_ip)

        return user
    except Exception as e:
        module.fail_json(msg=str(e))


def update_user(module, oneandone_conn):
    """
    Update a user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    _user_id = module.params.get('user')
    _description = module.params.get('description')
    _email = module.params.get('email')
    _password = module.params.get('password')
    _state = module.params.get('user_state')
    _user_ips = module.params.get('user_ips')
    _ip = module.params.get('remove_ip')
    _active = module.params.get('active')
    _key = module.params.get('change_api_key')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    wait_interval = module.params.get('wait_interval')

    changed = False

    user = _find_user(oneandone_conn, _user_id)

    try:
        if _description or _email or _password or _state:
            user = oneandone_conn.modify_user(
                user_id=user['id'],
                description=_description,
                email=_email,
                password=_password,
                state=_state)
            changed = True

        if _user_ips:
            user = _add_user_ip(module=module,
                                oneandone_conn=oneandone_conn,
                                user_id=user['id'],
                                user_ips=_user_ips)
            changed = True

        if _ip:
            user = _remove_user_ip(module=module,
                                   oneandone_conn=oneandone_conn,
                                   user_id=user['id'],
                                   user_ip=_ip)
            changed = True

        if _active:
            user = _modify_user_api(module=module,
                                    oneandone_conn=oneandone_conn,
                                    user_id=user['id'],
                                    active=_active)
            changed = True

        if _key and _key is True:
            user = _change_api_key(module=module,
                                   oneandone_conn=oneandone_conn,
                                   user_id=user['id'])
            changed = True

        if wait:
            _wait_for_user_creation_completion(
                oneandone_conn, user['id'], wait_timeout, wait_interval)

        return (changed, user)
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
    wait_interval = module.params.get('wait_interval')

    try:
        user = oneandone_conn.create_user(
            name=name,
            password=password,
            email=email,
            description=description)

        if wait:
            _wait_for_user_creation_completion(
                oneandone_conn, user['id'], wait_timeout, wait_interval)

        changed = True if user else False

        return (changed, user)
    except Exception as e:
        module.fail_json(msg=str(e))


def remove_user(module, oneandone_conn):
    """
    Delete a new user

    module : AnsibleModule object
    oneandone_conn: authenticated oneandone object
    """
    user_id = module.params.get('name')
    _user = _find_user(oneandone_conn, user_id)

    try:
        user = oneandone_conn.delete_user(_user['id'])

        changed = True if user else False

        return (changed, {
            'id': user['id'],
            'name': user['name']
        })
    except Exception as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            auth_token=dict(
                type='str',
                default=os.environ.get('ONEANDONE_AUTH_TOKEN')),
            api_url=dict(
                type='str',
                default=os.environ.get('ONEANDONE_API_URL')),
            name=dict(type='str'),
            user_id=dict(type='str'),
            description=dict(type='str'),
            password=dict(type='str'),
            email=dict(type='str'),
            active=dict(type='bool'),
            user_ips=dict(type='list', default=[]),
            remove_ip=dict(type='str'),
            change_api_key=dict(type='bool', default=False),
            user_state=dict(
                choices=USER_STATES),
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
        if not module.params.get('name'):
            module.fail_json(
                msg="'name' parameter is required to delete a user.")
        try:
            (changed, user) = remove_user(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))
    elif state == 'update':
        if not module.params.get('user'):
            module.fail_json(
                msg="'user' parameter is required to update a user.")
        try:
            (changed, user) = update_user(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    elif state == 'present':
        for param in ('name', 'password'):
            if not module.params.get(param):
                module.fail_json(
                    msg="%s parameter is required for new users." % param)
        try:
            (changed, user) = create_user(module, oneandone_conn)
        except Exception as e:
            module.fail_json(msg=str(e))

    module.exit_json(changed=changed, user=user)


if __name__ == '__main__':
    main()
