# Installing Telemetry
1. Ensure that all required [pre-requisites](../PreRequisites/Telemetry_Visualization_PreReqs.md) and [input parameters](../Input_Parameter_Guide/Telemetry_Visualization_Parameters) are entered for telemetry.

2. Once `control_plane.yml` and `omnia.yml` are executed, run the following commands from `omnia/telemetry`:

`ansible-playbook telemetry.yml`

>> **Note**: Telemetry Collection is only initiated on iDRACs on AWX that have a datacenter license and are running a firmware version of 4 or higher.

## Adding a New Node to Telemetry
After initiation, new nodes can be added to telemetry by running the following commands from `omnia/telemetry`:
		
`ansible-playbook add_idrac_node.yml`

>> **Note**: Omnia creates a log file which is available at: `/var/log/omnia_telemetry.log`.  