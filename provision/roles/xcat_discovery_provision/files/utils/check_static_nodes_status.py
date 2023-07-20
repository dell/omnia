import subprocess

def run_cmd(cmd):
    run = subprocess.run(cmd,shell=True,capture_output=True,text=True)

    if 'ERROR' in run.stderr:
        return False,run.stderr,run.stdout
    else:
        return True,run.stderr,run.stdout

def get_static_nodes():
    cmd = 'lsdef -t group -o bmc_static | grep members | sed -n "/members=/s/    members=//p"'
    status,err,out = run_cmd(cmd)
    if status:
        return out.split(',')
    else:
        print(f" No group with bmc_static found, Error : {err} ")

def check_static_nodes(nodelist):
    bmc_list = list()
    for node in nodelist:
        node=node.strip()
        cmd = '''lsdef {node} -i status -c | sed -n "/{node}: status=/s/{node}: status=//p"'''.format(node=node)
        status,err,out = run_cmd(cmd)
        if status:
            if len(out) == 1:
                bmc_list.append(node)

    bmc_string = ' '.join(map(str,bmc_list))
    print(bmc_string)


check_static_nodes(get_static_nodes())
