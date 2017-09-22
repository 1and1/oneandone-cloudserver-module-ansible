# Ansible Module

Version: **oneandone-cloudserver-module-ansible v1.0.0**

## Table of Contents

* [Description](#description)
* [Getting Started](#getting-started)
* [Installation](#installation)
* [Usage](#usage)
    * [Authentication](#authentication)
    * [Ansible Playbooks](#ansible-playbooks)
    * [Execute a Playbook](#execute-a-playbook)
    * [Wait for Requests](#wait-for-requests)
    * [Wait for Services](#wait-for-services)
    * [Incrementing Servers](#incrementing-servers)
    * [SSH Key Authentication](#ssh-key-authentication)
* [Reference](#reference)
    * [oneandone_server](#oneandone_server)
    * [oneandone\_firewall\_policy](#oneandone_firewall_policy)
    * [oneandone\_load\_balancer](#oneandone_load_balancer)
    * [oneandone\_monitoring\_policy](#oneandone_monitoring_policy)
    * [oneandone\_private\_network](#oneandone_private_network)
    * [oneandone\_public\_ip](#oneandone_public_ip)
    * [oneandone\_vpn](#oneandone_vpn)
    * [oneandone\_users](#oneandone_users)
    * [oneandone\_roles](#oneandone_roles)    
* [Examples](#examples)
* [Support](#support)
* [Testing](#testing)
* [Contributing](#contributing)

## Description

Ansible is an IT automation tool that allows users to configure, deploy, and orchestrate advanced tasks such as continuous deployments or zero-downtime rolling updates. The 1&1 Cloud Server module for Ansible leverages the 1&1 Cloud Server API. For more information on the Ansible Module see the [1&1 Community Portal](https://www.1and1.com/cloud-community/).

## Getting Started

The 1&1 module for Ansible has the following requirements:

* 1&1 account (API key)
* Python
* [Ansible](https://www.ansible.com/)
* [1&1 Python Cloud Server SDK](https://www.1and1.com/cloud-community/develop/11-python-cloud-server-sdk/get-the-sdk/)

Before you begin, you need to have a 1&1 account.

To enable the API token:

1. Log in to your 1&1 Control Panel and select the relevant package.
2. Click **1&1 Cloud Panel** from the Cloud Server section of the control panel.
3. Select **Users** from the **Management** section of the **Infrastructure** menu.
4. Select the user who needs the API token.
5. In the API section in the lower part of the screen, click **Disabled** next to the API KEY.
6. Click **OK** to activate the API key.

Ansible must also be installed before the 1&1 module can be used. Please review the official [Ansible Documentation](http://docs.ansible.com/ansible/intro_installation.html) for more information on installing Ansible.

The 1&1 module requires the 1&1 Python Cloud Server SDK to be installed. This can easily be accomplished with Python PyPI:

    pip install 1and1

## Installation

1. Download the 1&1 Cloud Server module for Ansible from GitHub. This can be accomplished a few different ways such as downloading and extracting the archive using `curl` or cloning the GitHub repository locally.

**Download and extract with `curl`:**

        mkdir -p oneandone-cloudserver-module-ansible && curl -L https://github.com/StackPointCloud/oneandone-cloudserver-module-ansible/tarball/master | tar zx -C oneandone-cloudserver-module-ansible/ --strip-components=1

**Clone the GitHub repository locally:**

        git clone https://github.com/StackPointCloud/oneandone-cloudserver-module-ansible

2. Ansible must be made aware of the new module path. This too can be accomplished a few different ways depending on your requirements and environment.

    * Ansible configuration file: `ansible.cfg`
    * Environment variable: `ANSIBLE_LIBRARY`
    * Command line parameter: `ansible-playbook --module-path [path]`

**Method 1: Update the Ansible configuration with the module path.**

To include the path globally for all users, edit the `/etc/ansible/ansible.cfg` file and add `library = /path/to/module/oneandone` under the **[default]** section. For example:

        [default]
        library = /path/to/oneandone-cloudserver-module-ansible/oneandone

    Note that the Ansible configuration file is read from several locations in the following order:

    * `ANSIBLE_CONFIG` environment variable path
    * `ansible.cfg` from the current directory
    * `.ansible.cfg` in the user home directory
    * `/etc/ansible/ansible.cfg`

**Method 2: Set the module path using an environment variable.**

This variable will be lost once the terminal session is closed:

        export ANSIBLE_LIBRARY=/path/to/oneandone-cloudserver-module-ansible/oneandone

**Method 3: Override the module path with an `ansible-playbook` command line parameter:**

        ansible-playbook --module-path /path/to/oneandone-cloudserver-module-ansible/oneandone playbook.yml

## Usage

### Authentication

Credentials can be supplied using the following:

* `ONEANDONE_AUTH_TOKEN` environment variable.
* **auth_token** Playbook parameter.

### Ansible Playbooks

Ansible uses YAML manifest files called Playbooks. The Playbook will describe the infrastructure to build and is processed from top down. Here is a simple Playbook that will provision two identical servers:

`example.yml`:

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Provision a set of servers
          oneandone_server:
              auth_token: {your_api_key}          
              hostname: server%02d
              auto_increment: true
              appliance: 8E3BAA98E3DFD37857810E0288DD8FBA
              count: 2
              datacenter: US
              ssh_key: AAAAB3NzaC1yc2EAAAADAQABAAACAQDPCNA2YgJ...user@hostname
              state: present
          register: oneandone

### Execute a Playbook

The `ansible-playbook` command will execute the above Playbook:

    ansible-playbook example.yml

### Wait for Requests

When a request to create a resource (such as a server) is submitted to the 1&1 Cloud Server API, that request is accepted immediately while the provisioning occurs on the backend. This means the request can appear  to have finished while provisioning is still occurring.

Sometimes requests must be told to wait until they finish before continuing to provision dependent resources. For example, a server must finish provisioning before a new IP address can be added to the server.

The 1&1 Cloud Server module includes two resource parameters to address this scenario:

* **wait** (default: true)
* **wait_timeout** (default: 600 seconds)
* **wait_interval** (default: 5 seconds)

By default, the module will wait until a resource is finished provisioning before continuing to process further resources defined in the Playbook.

### Wait for Services

There may be occasions where additional waiting is required. For example, a server may be finished provisioning and shown as available, but IP allocation and network access is still pending. The built-in Ansible module **wait_for** can be invoked to monitor SSH connectivity.

    - name: Wait for SSH connectivity
      wait_for:
          port: 22
          host: "{{ item.public_ip }}"
          search_regex: OpenSSH
          delay: 10
      with_items: "{{ oneandone.machines }}"

### Incrementing Servers

The **1&1** module will provision a number of identical and fully operational servers based on the **count** parameter. A **count** parameter of 10 will provision ten servers with system volumes and network connectivity.

The server **name** parameter with a value of `server%02d` will appended the name with the incremental count. For example, server01, server02, server03, and so forth.

The **auto_increment** parameter can be set to `false` to disable this feature and provision a single server.

## Reference

### oneandone_server

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Provision a set of servers
          oneandone_server:
            auth_token: {your_api_key}       
            hostname: server%02d
            auto_increment: true
            appliance: {appliance_id}
            fixed_instance_size: S
            datacenter: US
            state: present

#### Parameter Reference

The following parameters are supported:
                      
| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| hostname | **yes** | string | none | The name of the server(s). |
| fixed_instance_size | **yes** * | string | none | Size of the ID desired for the server. ('S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL', '5XL') |
| vcore | **yes** * | int | none | The total number of processors. |
| cores_per_processor | **yes** * | int | none | The number of cores per processor. |
| ram | **yes** * | float | none | The amount of RAM memory. |
| hdds | **yes** * | array | none | A list of hard disk objects with nested `size` and `is_main` properties. |
| size | **yes** | integer | none | Size of the hard disk. |
| is_main | **yes** | boolean | none | Set true if it's main. |
| appliance | **yes** | string | none | Name or ID of the image that will be installed on server |
| description | no | string | none | The description of the server(s). |
| datacenter | no | string | none | ID of the datacenter where the server will be created. ('US', 'ES', 'DE', 'GB') |
| private_network | no | string | none | Name or ID of the private network to connect the server. |
| firewall_policy | no | string | none | Firewall policy's ID or name. If it is not provided, the server will assign the best firewall policy, creating a new one if necessary. If the parameter is sent with a 0 value, the server will be created with all ports blocked. |
| load_balancer | no | string | none | Name or ID of the load balancer to assign the server. |
| monitoring_policy | no | string | none | Name or ID of the monitoring policy to assign the server. |
| ssh_key | no | string | none | Put a valid public SSH Key to be copied into the server during creation. Then you will be able to access to the server using your SSH keys. |
| auto_increment | no | boolean | True | Whether or not to increment created servers. |
| count | no | integer | 1 | The number of servers to create. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. </br>Also used for delete operation (set to 'false' if you don't want to wait for each individual server to be deleted before moving on with other tasks.) |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create or terminate instances: **present**, absent, running, stopped |

** * ** - The server can be created using pre-defined instance sizes or by providing your own custom hardware values. If custom values are provided, then all four items must be provided (`vcore`, `cores_per_processor`, `ram`, and `hdds`).

### oneandone_firewall_policy

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a firewall policy
          oneandone_firewall_policy:
            auth_token: {your_api_key}       
            name: ansible_fw_policy
            description: Testing creation of firewall policies with ansible
            rules:
             -
               protocol: TCP
               port_from: 80
               port_to: 80
               source: 0.0.0.0
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | Firewall policy name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| firewall_policy | **yes** * | string | none | Firewall policy identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| rules | **yes** | array | none | A list of rules that will be set for the firewall policy. Each rule must contain **`protocol`** parameter, in addition to three optional parameters: `port_from`, `port_to`, and `source` |
| protocol | **yes** | string | none | Internet protocol ('TCP', 'UDP', 'ICMP', 'AH', 'ESP', 'GRE') |
| port_from | no | integer | none | First port in range. Required for UDP and TCP protocols, otherwise it will be set up automatically. |
| port_to | no | integer | none | Second port in range. Required for UDP and TCP protocols, otherwise it will be set up automatically. |
| source | no | string | 0.0.0.0 | IPs from which access is available. Setting 0.0.0.0 all IPs are allowed. |
| add_rules | no | array | none | A list of rules that will be added to an existing firewall policy. It's syntax is the same as the one used for `rules` parameter. Used in combination with **`update`** state. |
| remove_rules | no | array | none | A list of rule ids that will be removed from an existing firewall policy. Used in combination with **`update`** state. |
| add_server_ips | no | array | none | A list of servers/IPs to be assigned  to a firewall policy. Used in combination with **`update`** state. |
| remove_server_ips | no | array | none | A list of server IP ids to be unassigned  from a firewall policy. Used in combination with **`update`** state. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a firewall policy: **present**, absent, update |

### oneandone_load_balancer

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a load balancer
          oneandone_load_balancer:
            auth_token: {your_api_key}
            name: ansible load balancer
            description: Testing creation of load balancer with ansible
            health_check_test: TCP
            health_check_interval: 40
            persistence: true
            persistence_time: 1200
            method: ROUND_ROBIN
            datacenter: US
            rules:
             -
               protocol: TCP
               port_balancer: 80
               port_server: 80
               source: 0.0.0.0
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | Load balancer name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| load_balancer | **yes** * | string | none | Load balancer identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| health_check_test | **yes** | string | none | Type of the health check. At the moment, HTTP is not allowed. ('NONE', 'TCP', 'HTTP', 'ICMP') |
| health_check_interval | **yes** | integer | none | Health check period in seconds (5 - 300) |
| persistence | **yes** | boolean | none | Persistence |
| persistence_time | **yes** | integer | none | Persistence time in seconds. Required if persistence is enabled. (30 - 1200) |
| method | **yes** | string | none | Balancing procedure ('ROUND_ROBIN', 'LEAST_CONNECTIONS') |
| rules | **yes** | array | none | A list of rules that will be set for the load balancer. Each rule must contain **`protocol`**, **`port_balancer`**, and **`port_server`** parameters, in addition to `source`parameter, which is optional. |
| protocol | **yes** | string | none | Internet protocol ('TCP', 'UDP') |
| port_balancer | **yes** | integer | none | Port in balancer. Port 0 means every port. Only can be used if also 0 is set in port_server and health_check_test is set to NONE or ICMP. |
| port_server | **yes** | integer | none | Port in server. Port 0 means every port. Only can be used if also 0 is set in port_balancer and health_check_test is set to NONE or ICMP. |
| source | no | string | 0.0.0.0 | IPs from which access is available. Setting 0.0.0.0 all IPs are allowed. |
| add_rules | no | array | none | A list of rules that will be added to an existing load balancer. It's syntax is the same as the one used for `rules` parameter. Used in combination with **`update`** state. |
| remove_rules | no | array | none | A list of rule ids that will be removed from an existing load balancer. Used in combination with **`update`** state. |
| add_server_ips | no | array | none | A list of servers/IPs to be assigned  to a load balancer. Used in combination with **`update`** state. |
| remove_server_ips | no | array | none | A list of servers/IPs to be unassigned  from a load balancer. Used in combination with **`update`** state. |
| datacenter | no| string | none | ID of the datacenter where the load balancer will be created ('US', 'ES', 'DE', 'GB') |
| description | no| string | none | Description of the load balancer |
| health_check_path | no| string | none | Url to call for cheking. Required for HTTP health check. |
| health_check_parse | no| string | none | Regular expression to check. Required for HTTP health check. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a load balancer: **present**, absent, update |

### oneandone_monitoring_policy

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a monitoring policy
          oneandone_monitoring_policy:
            auth_token: {your_api_key}       
            name: ansible monitoring policy
            description: Testing creation of a monitoring policy with ansible
            email: your@email.com
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

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | Monitoring policy name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| monitoring_policy | **yes** * | string | none | Monitoring policy identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| agent | **yes** | string | none | Set true for using agent. |
| email | **yes** | string | none | User's email. |
| thresholds | **yes** | array | none | A list of five threshold objects that must be provided to be set for the monitoring policy (**`cpu`**, **`ram`**, **`disk`**, **`internal_ping`**, and **`transfer`**). Each of those five threshold objects must contain **`warning`** and **`critical`** objects, each of which must contain **`alert`** and **`value`** parameters.  |
| cpu | **yes** | object | none | Consumption limits of CPU. |
| ram | **yes** | object | none | Consumption limits of RAM. |
| disk | **yes** | object | none | Consumption limits of hard disk. |
| internal_ping | **yes** | object | none | Response limits of internal ping. |
| transfer | **yes** | object | none | Consumption limits for transfer. |
| warning | **yes** | object | none | Set limits for warning. </br>**Must be set for all five threshold objects (`cpu`, `ram`, `disk`, `internal_ping`, and `transfer`). Must contain `alert` and  `value` parameters.** |
| critical | **yes** | object | none | Set limits for critical case. </br>**Must be set for all five threshold objects (`cpu`, `ram`, `disk`, `internal_ping`, and `transfer`). Must contain `alert` and  `value` parameters.** |
| alert | **yes** | boolean | none | Enable alert. </br>**Each `warning` and `critical` object must contain this parameter.** |
| value | **yes** | integer | none | Advise when this value is exceeded. Depending on the threshold object, the value represents either (%), (ms), or (kbps). </br></br>The following are the valid values for each of the threshold objects: </br></br> **cpu, ram, disk (%)**:</br> warning: min. 1, max. 95 </br> critical: max. 100 </br></br> **internal_ping (ms)**:</br> warning: min. 1 </br> critical: max. 100 </br></br> **transfer (kbps)**:</br> warning: min. 1 </br> critical: max. 2000 |
| ports | **yes** | array | none | Array of ports that will be monitoring. Each port object must contain `protocol`, `port`, `alert_if`, and `email_notification` parameters. |
| protocol | **yes** | string | none | Internet protocol. ('TCP', 'UDP') |
| port | **yes** | integer | none | Port number. (1 - 65535) |
| alert_if | **yes** | string | none | Case of alert. ('RESPONDING', 'NOT_RESPONDING') |
| email_notification | **yes** | boolean | none | Set true for sending e-mail notifications. |
| processes | **yes** | array | none | Array of processes that will be monitoring. Each port object must contain `process`, `alert_if`, and `email_notification` parameters. |
| process | **yes** | string | none | Name of the process. |
| alert_if | **yes** | string | none | Case of alert. 'RUNNING', 'NOT_RUNNING') |
| description | no | string | none | Monitoring policy description. |
| add_ports | no | array | none | A list of `port` objects that will be added to an existing monitoring policy. Used in combination with **`update`** state. |
| update_ports | no | array | none | A list of existing monitoring policy `port` objects that will be updated. Their definition is the same as regular port objects, with an addition of port `id` parameter which must be provided. Used in combination with **`update`** state. |
| remove_ports | no | array | none | A list of port ids that represent port objects which will be removed from the monitoring policy. Used in combination with **`update`** state. |
| add_processes | no | array | none | A list of `process` objects that will be added to an existing monitoring policy. Used in combination with **`update`** state. |
| update_processes | no | array | none | A list of existing monitoring policy `process` objects that will be updated. Their definition is the same as regular process objects, with an addition of process `id` parameter which must be provided. Used in combination with **`update`** state. |
| remove_processes | no | array | none | A list of process ids that represent process objects which will be removed from the monitoring policy. Used in combination with **`update`** state. |
| add_servers | no | array | none | A list of servers ids to be attached to the monitoring policy. Used in combination with **`update`** state. |
| remove_servers | no | array | none | A list of server ids to be detached  from the monitoring policy. Used in combination with **`update`** state. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a monitoring policy: **present**, absent, update |

### oneandone_private_network

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:

        - name: Create a private network
          oneandone_private_network:
            auth_token: {your_api_key}
            name: ansible_private_network
            description: Testing creation of a private network with ansible
            network_address: 70.35.193.100
            subnet_mask: 255.0.0.0
            datacenter: DE
            wait: false

        - name: Update a private network
          oneandone_private_network:
            auth_token: {your_api_key}
            private_network: ansible_private_network
            description: Testing the update of a private network with ansible
            network_address: 192.168.1.1
            subnet_mask: 255.255.255.0
            datacenter: DE
            wait: false
            state: update
        
        - name: Attach servers to a private network
          oneandone_private_network:
            auth_token: {your_api_key}
            private_network: ansible_private_network
            add_members:
             - E7D36EC025C73796035BF4F171379025
             - 8A7D5122BDC173B6E52223878CEF2748
             - D5C5C1D01249DE9B88BE3DAE973AA090
            state: update
            wait: false

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | Private network name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| private_network | **yes** * | string | none | Private network identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| description | no | string | none | Private network description. |
| datacenter | no | string | none | ID of the datacenter where the private network will be created. ('US', 'ES', 'DE', 'GB') |
| network_address | no | string | none | Private network address (valid IP). |
| subnet_mask | no | string | none | Subnet mask (valid subnet for the given IP). |
| add_members | no | array | none | Array of desired servers ids to be attached to a private network. |
| remove_members | no | string | none | Array of desired servers ids to be detached from a private network.|
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, update a private network, attach/detach servers to/from a private network: **present**, absent, update |

### oneandone_public_ip

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a public IP
          oneandone_public_ip:
            auth_token: {your_api_key}
            datacenter: US
            reverse_dns: test.com
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| public_ip_id | **yes** * | string | none | ID or of the public IP that will be used in update or delete requests. Required for `absent` and `update` states. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| datacenter | no | string | 'US' | ID of the datacenter where the IP will be created (only for unassigned IPs). ('US', 'ES', 'DE', 'GB') |
| reverse_dns | no | string | none | Reverse DNS name. |
| type | no | string | 'IPV4' | Type of IP. Currently, only IPV4 is supported. ('IPV4', 'IPV6') |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a public ip: **present**, absent, and update. |

### oneandone_vpn

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a VPN
          oneandone_vpn:
            auth_token: {your_api_key}
            datacenter: US
            name: ansible VPN
            description: Create a VPN using ansible
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | VPN name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| vpn | **yes** * | string | none | VPN identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| description | no | string | none | VPN description. |
| datacenter | no | string | none | ID of the datacenter where the VPN will be created. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a VPN: **present**, absent, and update. |

### oneandone_users

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a user
          oneandone_users:
            auth_token: {your_api_key}
            name: ansible_test_user
            description: Create a user with ansible - test
            password: {password}
            email: user@example.com
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| description | no | string | none | User's description. |
| name | **yes** | string | none | User's name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| user | **yes** * | string | none | User identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| description | no | string | none | User's description. |
| password | **yes** | string | none | User's password. Pass must contain at least 8 characters using uppercase letters, numbers and other special symbols. |
| description | no | string | none | User's description. |
| email | no | string | none | User's e-mail. |
| user_state | no | string | none | Allows to enable or disable users. ('ACTIVE', 'DISABLE') |
| active | no | boolean | false | Set true for enabling API |
| user_ips | no | string | none | Array of new IPs from which access to API will be available. |
| remove_ip | no | string | none | An IP that will be deleted and API access for it will be forbidden. |
| change_api_key | no | string | none | User's API key (token for accessing the API) will be changed to the provided value. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a user: **present**, absent, and update. |

### oneandone_roles

#### Example Syntax

    ---
    - hosts: localhost
      connection: local
      gather_facts: false
    
      tasks:
        - name: Create a VPN
          oneandone_vpn:
            auth_token: {your_api_key}
            name: ansible_test_role
            wait: true
            wait_timeout: 500

#### Parameter Reference

The following parameters are supported:

| Name | Required | Type | Default | Description |
| --- | :-: | --- | --- | --- |
| auth_token | **yes** | string | none | Used for authorization of the request towards the API. This token can be obtained from the CloudPanel in the Management-section below Users.hostname |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| name | **yes** | string | none | Role name used with `present` state. Used as identifier (id or name) when used with `absent` state. |
| role | **yes** * | string | none | Role identifier (id or name). Must be provided with `update` state. |
| api_url | **yes** | string | https://cloudpanel-api.1and1.com/v1 | Used when providing a custom API URL |
| description | no | string | none | Role description. |
| role_state | no | string | none | Allows to enable or disable the role. ('ACTIVE', 'DISABLE') |
| servers | no | object | none | Servers permissions object attributes (boolean values)</br> `show`- Allows to list servers. </br> `create`- Allows to create servers. </br> `delete`- Allows to delete servers. </br> `set_name`- Allows to change server name. </br> `set_description`- Allows to change server description. </br> `start`- Allows to start servers. </br> `restart`- Allows to restart servers. </br> `shutdown`- Allows to shutdown servers. </br> `resize`- Allows to resize servers. </br> `reinstall`- Allows to reinstall servers. </br> `clone`- Allows to clone servers. </br> `manage_snapshot`- Allows to manage snapshots. </br> `assign_ip`- Allows to assign new IPs </br> `manage_dvd`- Allows to manage DVD images. </br> `access_kvm_console`- Allows to access servers using KVM console. |
| images | no | object | none | Images permissions object attributes (boolean values)</br> `show`- Allows to list images. </br> `create`- Allows to create images. </br> `delete`- Allows to delete images. </br> `set_name`- Allows to change image name. </br> `set_description`- Allows to change image description. </br> `disable_automatic_creation`- Allows to change image creation policy. |
| shared_storages | no | object | none | Shared storages permissions object attributes (boolean values)</br> `show`- Allows to list shared storages. </br> `create`- Allows to create shared storages. </br> `delete`- Allows to delete shared storages. </br> `set_name`- Allows to change shared storage name. </br> `set_description`- Allows to change shared storage description. </br> `manage_attached_servers`- Allows to manage servers attached. </br> `access`- Allows to manage shared storage permissions. </br> `resize`- Allows to resize shared storages. |
| firewalls | no | object | none | Firewall policies permissions object attributes (boolean values)</br> `show`- Allows to list firewall policies. </br> `create`- Allows to create firewall policies. </br> `delete`- Allows to delete firewall policies. </br> `set_name`- Allows to change firewall policy name. </br> `set_description`- Allows to change firewall policy description. </br> `manage_rules`- Allows to manage firewall policy rules. </br> `manage_attached_server_ips`- Allows to add or remove servers from firewall policies. </br> `clone`- Allows to clone firewall policies. |
| load_balancers | no | object | none | Load balancers permissions object attributes (boolean values)</br> `show`- Allows to list load balancers. </br> `create`- Allows to create load balancers. </br> `delete`- Allows to delete load balancers. </br> `set_name`- Allows to change load balancer name. </br> `set_description`- Allows to change load balancer description. </br> `manage_rules`- Allows to manage load balancer rules. </br> `manage_attached_server_ips`- Allows to add or remove servers from load balancers. </br> `modify`- Allows to edit load balancers. |
| ips | no | object | none | Public IPs permissions object attributes (boolean values)</br> `show`- Allows to list public IPs. </br> `create`- Allows to create public IPs. </br> `delete`- Allows to delete public IPs. </br> `release`- Allows to release IPs. </br> `set_reverse_dns`- Allows to change reverse DNS name. |
| private_networks | no | object | none | Private networks permissions object attributes (boolean values)</br> `show`- Allows to list private networks. </br> `create`- Allows to create private networks. </br> `delete`- Allows to delete private networks. </br> `set_name`- Allows to change private network name. </br> `set_description`- Allows to change private network description. </br> `set_network_info`- Allows to edit private network configuration. </br> `manage_attached_servers`- Allows to manage servers attached. |
| vpns | no | object | none | VPNs permissions object attributes (boolean values)</br> `show`- Allows to list VPNs. </br> `create`- Allows to create VPNs. </br> `delete`- Allows to delete VPNs. </br> `set_name`- Allows to change VPN name. </br> `set_description`- Allows to change VPN description. </br> `download_file`- Allows to download VPN configuration file. |
| monitoring_centers | no | object | none | Monitoring center permissions object attributes (boolean values)</br> `show`- Allows to list monitored resources. |
| monitoring_policies | no | object | none | Monitoring policies permissions object attributes (boolean values)</br> `show`- Allows to list monitoring policies. </br> `create`- Allows to create monitoring policies. </br> `delete`- Allows to delete monitoring policies. </br> `set_name`- Allows to change monitoring policy name. </br> `set_description`- Allows to change monitoring policy description. </br> `set_email`- Allows to change monitoring policy email. </br> `modify_resources`- Allows to make changes to thresholds. </br> `manage_ports`- Allows to add or remove port alerts to monitoring policy. </br> `manage_processes`- Allows to add or remove process alerts to monitoring policy. </br> `manage_attached_servers`- Allows to manage servers attached to monitoring policy. </br> `clone`- Allows to clone monitoring policies. |
| backups | no | object | none | Backups permissions object attributes (boolean values)</br> `show`- Allows to list backup accounts. </br> `create`- Allows to create backup accounts. </br> `delete`- Allows to delete backup accounts. |
| logs | no | object | none | Logs permissions object attributes (boolean values)</br> `show`- Allows to list logs. |
| users | no | object | none | Users permissions object attributes (boolean values)</br> `show`- Allows to list users. </br> `create`- Allows to create users. </br> `delete`- Allows to delete users. </br> `set_description`- Allows to change user description. </br> `set_email`- Allows to change user e-mail. </br> `set_password`- Allows to change user password. </br> `manage_api`- Allows to manage the Cloud Panel from the API. </br> `enable`- Allows to enable users. </br> `disable`- Allows to disable users. </br> `change_role`- Allows to change user role. |
| roles | no | object | none | Roles permissions object attributes (boolean values)</br> `show`- Allows to list roles. </br> `create`- Allows to create roles. </br> `delete`- Allows to delete roles. </br> `set_name`- Allows to change role name. </br> `set_description`- Allows to change role description. </br> `manage_users`- Allows to manage users' role. </br> `modify`- Allows to change role permissions. </br> `clone`- Allows to clone roles. |
| usages | no | object | none | Usages permissions object attributes (boolean values)</br> `show`- Allows to list usages. |
| interactive_invoices | no | object | none | Interactive invoices permissions object attributes (boolean values)</br> `show`- Allows to list interactive invoices. |
| add_users | no | array | none | A list of user ids that will be added to an existing role. |
| remove_users | no | array | none | A list of user ids that will be removed from an existing role. |
| role_clone_name | no | string | none | A name that will be assigned to the cloned role. |
| wait | no | boolean | true | Wait for the instance to be in state 'running' before continuing. |
| wait_timeout | no | integer | 600 | The number of seconds until the wait ends. |
| wait_interval | no | integer | 5 | The number of seconds between each request to check status. |
| state | no | string | present | Create, delete, or update a VPN: **present**, absent, and update. |

## Examples

The following example demonstrates creating a firewall policy, monitoring policy, two servers (one using fixed_size_instance, the other custom hardware) with the associated policies applied, and both added to a private network:

	---
	- hosts: localhost
	  connection: local
	  gather_facts: True

	  tasks:
	    - name: Create a firewall policy
	      oneandone_firewall_policy:
		name: ansible firewall policy
		description: Testing creation of firewall policies with ansible
		rules:
		 -
		   protocol: TCP
		   port_from: 80
		   port_to: 80
		   source: 0.0.0.0
		wait: true
		wait_timeout: 500
	      register: fw_policy

	    - name: Create a monitoring policy
	      oneandone_monitoring_policy:
		name: ansible monitoring policy
		description: Testing creation of a monitoring policy with ansible
		email: amel@stackpointcloud.com
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
	      register: mp

	    - name: Create server using custom hardware
	      oneandone_server:
		hostname: server_custom_size
		description: testing server creation with ansible
		auto_increment: true
		appliance: 8E3BAA98E3DFD37857810E0288DD8FBA
		vcore: 2
		cores_per_processor: 1
		ram: 1
		hdds:
		 -
		   is_main: true
		   size: 20
		 -
		   is_main: false
		   size: 20
		datacenter: US
		firewall_policy: "{{ fw_policy.firewall_policy.name }}"
		private_network: backup_network
		monitoring_policy: "{{ mp.monitoring_policy.name }}"
		state: present

	    - name: Create server using a fixed instance size
	      oneandone_server:
		hostname: server_fixed_size
		description: testing server creation with ansible
		auto_increment: true
		appliance: 8E3BAA98E3DFD37857810E0288DD8FBA
		fixed_instance_size: S
		datacenter: US
		firewall_policy: "{{ fw_policy.firewall_policy.name }}"
		private_network: backup_network
		monitoring_policy: "{{ mp.monitoring_policy.name }}"
		state: present


## Support

You are welcome to contact us with questions or comments using the **Community** section of the [1&1 Cloud Community](https://www.1and1.com/cloud-community). Please report any feature requests or issues using GitHub issue tracker.

* [1&1 Cloud Server API](https://cloudpanel-api.1and1.com/documentation/v1/en/documentation.html) documentation.
* Ask a question or discuss at [1&1 Cloud Community](https://www.1and1.com/cloud-community).
* Report an [issue here](https://github.com/1and1/oneandone-cloudserver-module-ansible/issues).
* More examples are located in the [GitHub repository](https://github.com/1and1/oneandone-cloudserver-module-ansible/tree/master/examples) `examples` directory.

## Testing

Change into the `examples` directory and execute the Playbooks.

    cd examples
    ansible-playbook server_create.yml

## Contributing

1. Fork the repository ([https://github.com/1and1/oneandone-cloudserver-module-ansible/fork](https://github.com/1and1/oneandone-cloudserver-module-ansible/fork))
2. Create your feature branch (git checkout -b my-new-feature)
3. Commit your changes (git commit -am 'Add some feature')
4. Push to the branch (git push origin my-new-feature)
5. Create a new Pull Request
