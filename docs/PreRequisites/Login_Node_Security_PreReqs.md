# Pre-requisites Before Enabling Security: Login Node

* Verify that the login node host name has been set. If not, use the following steps to set it.
	* Set hostname of the login node to hostname.domainname format using the below command:
	`hostnamectl set-hostname <hostname>.<domainname>`
	>>Eg: `hostnamectl set-hostname login-node.omnia.test`
	* Add the set hostname in `/etc/hosts` using vi editor.

	`vi /etc/hosts`

    * Add the IP of the login node with the above hostname using `hostnamectl` command in last line of the file.
  
	__Eg:__  xx.xx.xx.xx <hostname>
	
>> __Note:__ 
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods. 
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.
