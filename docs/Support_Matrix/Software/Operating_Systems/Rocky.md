# Rocky
| OS Version     	| Control Plane 	| Compute Nodes 	|
|----------------	|-------------------|---------------	|
| 8.4            	| Yes               | Yes           	|
| 8.5            	| Yes               | Yes           	|

>> **Note**: Always deploy the Minimal Edition of the OS on Compute Nodes


## Using BeeGFS on Rocky

| OS version   	| BeeGFS Client Version       	| Status        	|
|-----------	|----------------------------	|---------------	|
| Rocky-8.5 	| 7.2.4                      	| Not Supported 	|
| Rocky-8.5 	| 7.2.5                      	| Not Supported 	|
| Rocky-8.5 	| 7.2.6                      	| Supported     	|
| Rocky-8.5 	| 7.3.0                      	| Supported     	|

>> **Note**:
>> * At any given point, the client and management BeeGFS servers must be running the same major version of BeeGFS (ie 7.x). However, minor versions need not match (ie, management **7.x**.y and client **7.x**.z is supported).
>> * Upgrading BeeGFS to 7.3 using `omnia.yml` is not supported