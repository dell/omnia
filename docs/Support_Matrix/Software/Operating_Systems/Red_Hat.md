# Red Hat Enterprise Linux

| OS Version     	| Control Plane 	    | Compute Nodes 	|
|----------------	|--------------------	|---------------	|
| 8.1            	| No                 	| Yes           	|
| 8.2            	| No                 	| Yes           	|
| 8.3               | __Yes__               | Yes           	|
| 8.4            	| Yes *                 | Yes           	|
| 8.5            	| Yes *                	| Yes           	|
| 8.6               | Yes *                 | Yes           	|

>> **Note**: 
>> * Always deploy the Minimal Edition of the OS on compute nodes.
>> *  While Omnia may work with Red Hat 8.3 and above, all Omnia testing was done with Red Hat 8.3 on the control plane. All minor versions of Red Hat 8 are supported on the compute nodes.

## Using BeeGFS on Red Hat
| OS version   	| BeeGFS Client Version        	| Status        	|
|-----------	|----------------------------	|---------------	|
| RHEL-8.0  	| 7.2                        	| Supported     	|
| RHEL-8.0  	| 7.2.6                      	| Supported     	|
| RHEL-8.3  	| 7.2                        	| Not Supported 	|
| RHEL-8.3  	| 7.2.1                      	| Supported     	|
| RHEL-8.3  	| 7.2.4                      	| Supported     	|
| RHEL-8.3  	| 7.2.1                      	| Supported     	|
| RHEL-8.3  	| 7.2.2                      	| Supported     	|
| RHEL-8.3  	| 7.2.5                      	| Supported     	|
| RHEL-8.3  	| 7.2.6                      	| Supported     	|
| RHEL-8.3  	| 7.3.0 upgrading from 7.2.x/7.2 | Not Supported 	|
| RHEL-8.3  	| 7.x client , 7.y mgmtd   	    | Not Supported 	|
| RHEL-8.3  	| 7.2.6                      	| Supported     	|
| RHEL-8.3  	| 7.2.6                      	| Supported     	|
| RHEL-8.3  	| 7.3.0                      	| Supported     	|

>> **Note**:
>> * At any given point, the client and management BeeGFS servers must be running the same major version of BeeGFS (ie 7.x). However, minor versions need not match (ie, management **7.x**.y and client **7.x**.z is supported).
>> * Upgrading BeeGFS to 7.3 using `omnia.yml` is not supported

## Red Hat Subscription
Before running `omnia.yml`, it is mandatory that red hat subscription be set up on compute nodes running Red Hat.
* To set up Red hat subscription, fill in the [rhsm_vars.yml file](../../../Input_Parameter_Guide/Control_Plane_Parameters/Device_Parameters/rhsm_vars.md). Once it's filled in, run the template using AWX or Ansible. <br>
* The flow of the playbook will be determined by the value of `redhat_subscription_method` in `rhsm_vars.yml`.
    - If `redhat_subscription_method` is set to `portal`, pass the values `username` and `password` on the AWX screen. For CLI, run the command: <br> `ansible-playbook rhsm_subscription.yml -i inventory -e redhat_subscription_username= "<username>" -e redhat_subscription_password="<password>"`
    - If `redhat_subscription_method` is set to `satellite`, pass the values `organizational identifier` and `activation key` on the AWX screen. For CLI, run the command: <br> `ansible-playbook rhsm_subscription.yml -i inventory -e redhat_subscription_activation_key= "<activation-key>" -e redhat_subscription_org_id ="<org-id>"`

## Red Hat Unsubscription
To disable subscription on Red Hat nodes, the `red_hat_unregister_template` has to be called in one of two ways:
1. On AWX, run the template `redhat_unregister_template`. On launching the template, the nodes present in the node inventory will be unregistered from red hat.
2. Using CLI, run the command: `ansible_playbook omnia/control_plane/rhsm_unregister.yml -i inventory`

## Kernel Updates on Red Hat
### Pre-requisites
1. Subscription should be available on nodes
2. Kernels to be upgraded should be available. To verify the status of the kernels, use `yum list kernel`
3. The input kernel revision cannot be a RHEL 7.x supported kernel version. e.g. “3.10.0-54.0.1” to “3.10.0-1160”.
4. Input needs to be passed during execution of the playbook.

### Executing the Kernel Upgrade:

Via CLI:
`cd omnia/control_plane` <br>
`ansible-playbook kernel_upgrade.yml -i inventory -e rhsm_kernel_version=x.xx.x-xxxx` <br>
Through AWX UI <br>
![img.png](../../../images/Execute_Kernel_Upgrade_UI.png)

>>**Note**: Omnia does not support roll-backs/downgrades of the Kernel.