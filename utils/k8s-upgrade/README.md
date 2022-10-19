In order to run this ipgrade , we need to run it incrementally 

That is upgraed the versions by major upgrades only

DO NOT SKIP TO THE FINAL VERSION 

Edit the inventory file with the master / node Ips to be upgraded

<pre>
Edit the variable.yml from: 
1.19.3 -->  1.20.15 
& run $ansible-playbook -i inventory main.yml 
then update from 
1.20.15 --> 1.21.14
& run $ansible-playbook -i inventory main.yml
then update from 
1.21.14 --> 1.22.15
& run $ansible-playbook -i inventory main.yml
then update from
1.22.15 --> 1.23.12
& run $ansible-playbook -i inventory main.yml
</pre>
