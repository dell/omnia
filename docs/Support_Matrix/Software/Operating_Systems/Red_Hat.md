# Red Hat Enterprise Linux

| OS Version     	| Control Plane 	    | Compute Nodes 	|
|----------------	|--------------------	|---------------	|
| 8.x            	| No                 	| Yes           	|
| 8.6            	| Yes                 	| Yes           	|

>> __Note:__ 
>> * Always deploy the Minimal Edition of the OS on Compute Nodes.
>> * Omnia currently only supports 8.6 on the control plane. All minor versions of Red Hat 8 are supported on the compute nodes.

## Using BeeGFS on Red Hat
| OS version   	| BeeGFS   Version           	| Status        	|
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
| Rocky-8.5 	| 7.2.4                      	| Not Supported 	|
| Rocky-8.5 	| 7.2.5                      	| Not Supported 	|
| Rocky-8.5 	| 7.2.6                      	| Supported     	|
| Rocky-8.5 	| 7.3.0                      	| Supported     	|
>> __Note:__
>> * At any given point, the client and management BeeGFS servers must be running the same major version of BeeGFS (ie 7.x). However, minor versions need not match (ie, management **7.x**.y and client **7.x**.z is supported).
>> * Upgrading BeeGFS to 7.3 using `omnia.yml` is not supported