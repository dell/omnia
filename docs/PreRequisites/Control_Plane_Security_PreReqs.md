# Pre-requisites Before Enabling Security: Control Plane

* Set hostname of control plane to hostname.domainname format using the below command:
`hostnamectl set-hostname <hostname>.<domainname>`
>>Eg: `hostnamectl set-hostname valdiationms.omnia.test`
>> **Note**: 
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods. 
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.

* Add the set hostname in `/etc/hosts` using vi editor.

`vi /etc/hosts`

* Add the IP of the control plane with the above hostname using `hostnamectl` command in the last line of the file.
>> Eg: xx.xx.xx.xx <hostname>
