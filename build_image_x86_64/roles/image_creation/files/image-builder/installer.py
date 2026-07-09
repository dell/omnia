import subprocess
import logging
import os
import pathmod
import tempfile
# Written Modules
from utils import cmd

class Installer:
    def __init__(self, pkg_man, cname, mname, helper_cname=None):
        self.pkg_man = pkg_man
        self.cname = cname
        self.mname = mname
        self.helper_cname = helper_cname  # Container with dnf for --installroot (dnf builds)

        # Create temporary directory for logs, cache, etc. for package manager
        os.makedirs(os.path.join(mname, "tmp"), exist_ok=True)
        self.tdir = tempfile.mkdtemp(prefix="image-build-")
        logging.info(f'Installer: Temporary directory for {self.pkg_man} created at {self.tdir}')

        if pkg_man == "dnf":
            # DNF complains if the log directory is not present
            os.makedirs(os.path.join(self.tdir, "dnf/log"))

    def install_repos(self, repos, repo_dest, proxy):
        # check if there are repos passed for install
        if repos is None or len(repos) == 0:
            logging.info("REPOS: no repos passed to install\n")
            return

        logging.info(f"REPOS: Installing these repos to {self.cname}")
        for r in repos:
            args = []
            logging.info(r['alias'] + ': ' + r['url'])
            if self.pkg_man == "zypper":
                args.append("-D")
                args.append(os.path.join(self.mname, pathmod.sep_strip(repo_dest)))
                args.append("addrepo")
                args.append("-f")
                args.append("-p")
                if 'priority' in r:
                    args.append(r['priority'])
                else:
                    args.append('99')
                args.append(r['url'])
                args.append(r['alias'])
            elif self.pkg_man == "dnf":
                # Write .repo file directly to the working container's mounted filesystem.
                # The helper container's dnf will find these under --installroot.
                repo_dir = os.path.join(self.mname, pathmod.sep_strip(repo_dest))
                os.makedirs(repo_dir, exist_ok=True)
                repo_content = f'[{r["alias"]}]\n'
                repo_content += f'name={r["alias"]}\n'
                repo_content += f'baseurl={r["url"]}\n'
                repo_content += 'enabled=1\n'
                repo_content += 'gpgcheck=0\n'
                if proxy != "":
                    repo_content += f'proxy={proxy}\n'
                with open(os.path.join(repo_dir, f'{r["alias"]}.repo'), 'w') as f:
                    f.write(repo_content)
                logging.info(f'Adding repo from: {r["url"]}')
                if "gpg" in r and r["gpg"]:
                    keys_dir = os.path.join(self.mname, 'etc/pki/rpm-gpg')
                    os.makedirs(keys_dir, exist_ok=True)
                    subprocess.run(
                        ['curl', '-sk', r["gpg"], '-o', os.path.join(keys_dir, f'{r["alias"]}.gpg')],
                        check=False
                    )
                continue
            elif self.pkg_man == "apt":
                # Create apt sources.list.d dir and write repo file
                apt_args = [self.cname, '--', '/bin/sh', '-c']
                repo_dir = pathmod.sep_strip(repo_dest)
                repo_url = r['url']
                repo_alias = r['alias']
                apt_cmd = f'mkdir -p {repo_dir} && '
                apt_dist = r.get('apt_dist', '')
                apt_comp = r.get('apt_comp', '')
                # Flat repos: apt_dist is './' or '.', or comp is a sentinel placeholder
                is_flat = apt_dist in ('./', '.') or apt_comp in ('', 'flat-repo-component')
                if apt_dist and apt_comp and not is_flat:
                    apt_cmd += 'echo "deb [trusted=yes] ' + repo_url + ' ' + apt_dist + ' ' + apt_comp + '" > ' + repo_dir + '/' + repo_alias + '.list'
                else:
                    apt_cmd += 'echo "deb [trusted=yes] ' + repo_url + ' ./" > ' + repo_dir + '/' + repo_alias + '.list'
                apt_args.append(apt_cmd)
                cmd(["buildah","run"] + apt_args)
                if "gpg" in r:
                    gpg_args = [self.cname, '--', '/bin/sh', '-c',
                                f'curl -fsSL {r["gpg"]} | gpg --dearmor -o /usr/share/keyrings/{r["alias"]}-keyring.gpg']
                    cmd(["buildah","run"] + gpg_args)
                continue
            elif self.pkg_man == "apk":
                # Create apk repositories directory
                args = [self.cname, '--', '/bin/sh', '-c', f'mkdir -p {pathmod.sep_strip(repo_dest)}']
                cmd(["buildah","run"] + args)

                # Add repo URL to repositories file
                repo_file = os.path.join(pathmod.sep_strip(repo_dest), r['alias'])
                args = [self.cname, '--', '/bin/sh', '-c', f'echo "{r["url"]}" > {repo_file}']
                cmd(["buildah","run"] + args)

                # Handle GPG key if provided
                if "gpg" in r:
                    args = [self.cname, '--', '/bin/sh', '-c', 'mkdir -p etc/apk/keys']
                    cmd(["buildah","run"] + args)
                    # Download and add GPG key
                    args = [self.cname, '--', '/bin/sh', '-c', f'curl -s {r["gpg"]} > etc/apk/keys/{r["alias"]}']
                    cmd(["buildah","run"] + args)
                return

            rc = cmd([self.pkg_man] + args)
            if rc != 0:
                raise Exception("Failed to install repo", r['alias'], r['url'])

            if proxy != "":
                if r['url'].endswith('.repo'):
                    repo_name = r['url'].split('/')[-1].split('.repo')[0] + "*"
                elif r['url'].startswith('https'):
                    repo_name = r['url'].split('https://')[1].replace('/','_')
                elif r['url'].startswith('http'):
                    repo_name = r['url'].split('http://')[1].replace('/','_')
                args = []
                args.append('config-manager')
                args.append('--save')
                args.append("--setopt=reposdir="+os.path.join(self.mname, pathmod.sep_strip(repo_dest)))
                args.append("--setopt=logdir="+os.path.join(self.tdir, self.pkg_man, "log"))
                args.append("--setopt=cachedir="+os.path.join(self.tdir, self.pkg_man, "cache"))
                args.append('--setopt=*.proxy='+proxy)
                args.append(repo_name)

                rc = cmd([self.pkg_man] + args)
                if rc != 0:
                    raise Exception("Failed to set proxy for repo", r['alias'], r['url'], proxy)

            if "gpg" in r:
                # Using rpm apparently works for both Yum- and Zypper-based distros.
                args = []
                if proxy != "":
                    arg_env = os.environ.copy()
                    arg_env['https_proxy'] = proxy
                args.append("--root="+self.mname)
                args.append("--import")
                args.append(r["gpg"])

                rc = cmd(["rpm"] + args)
                if rc != 0:
                    raise Exception("Failed to install gpg key for", r['alias'], "at URL", r['gpg'])

    def install_base_packages(self, packages, registry_loc, proxy):
        # check if there are packages to install
        if packages is None or len(packages) == 0:
            logging.warn("PACKAGES: no packages passed to install\n")
            return

        logging.info(f"PACKAGES: Installing these packages to {self.cname}")
        logging.info("\n".join(packages))

        args = []
        if self.pkg_man == "zypper":
            args.append("-n")
            args.append("-D")
            args.append(os.path.join(self.mname, pathmod.sep_strip(registry_loc)))
            args.append("-C")
            args.append(self.tdir)
            args.append("--no-gpg-checks")
            args.append("--installroot")
            args.append(self.mname)
            args.append("install")
            args.append("-l")
            args.extend(packages)
        elif self.pkg_man == "dnf":
            env = os.environ.copy()
            if proxy != "":
                env['http_proxy'] = proxy
                env['https_proxy'] = proxy
            helper = self.helper_cname if self.helper_cname else self.cname
            reposdir = os.path.join(self.mname, 'etc/yum.repos.d')
            rc = cmd(
                ["buildah", "run",
                 "--volume", f"{self.mname}:{self.mname}:z",
                 helper, "--",
                 "dnf", f"--installroot={self.mname}",
                 f"--setopt=reposdir={reposdir}",
                 "--setopt=logdir=/tmp",
                 "--setopt=cachedir=/tmp/dnf-cache",
                 "install", "-y", "--nogpgcheck"] + packages,
                env=env
            )
            if rc == 104:
                raise Exception("Installing base packages failed")
            if rc == 107:
                logging.warn("one or more RPM postscripts failed to run")
            return
        elif self.pkg_man == "apt":
            env = os.environ.copy()
            if proxy != "":
                env['http_proxy'] = proxy
                env['https_proxy'] = proxy
            # Disable SSL peer verification for apt (Pulp uses self-signed cert)
            logging.info("Configuring apt: disable SSL verify for Pulp repos")
            cmd(["buildah", "run", self.cname, "--", "bash", "-c",
                 'echo \'Acquire::https::Verify-Peer "false";\' > /etc/apt/apt.conf.d/99no-ssl-verify'],
                check=False, env=env)
            # Remove CUDA/nvidia repo sources inherited from base image
            # These repos have broken/missing packages that cause apt-get install to fail
            logging.info("Removing CUDA/nvidia repo sources to avoid broken dependencies")
            cmd(["buildah", "run", self.cname, "--", "bash", "-c",
                 'rm -f /etc/apt/sources.list.d/*cuda* /etc/apt/sources.list.d/*nvidia*'],
                check=False, env=env)
            # Run apt-get update with --allow-insecure-repositories for Pulp repos
            rc = cmd(["buildah", "run", "--env", "DEBIAN_FRONTEND=noninteractive",
                      self.cname, "--", "apt-get", "update",
                      "--allow-insecure-repositories"],
                     check=False, env=env)
            if rc != 0:
                logging.warn("apt-get update returned non-zero, continuing anyway")
            # Divert lvm2 postinst script to prevent hang in container
            # (lvm2 postinst runs vgscan/vgchange which hang with no block devices)
            logging.info("Diverting lvm2 postinst script to prevent hang")
            divert_postinst = "dpkg-divert --local --rename --divert /var/lib/dpkg/info/lvm2.postinst.real --add /var/lib/dpkg/info/lvm2.postinst 2>/dev/null || true"
            replace_postinst = "echo '#!/bin/sh' > /var/lib/dpkg/info/lvm2.postinst && echo 'exit 0' >> /var/lib/dpkg/info/lvm2.postinst && chmod +x /var/lib/dpkg/info/lvm2.postinst"
            postinst_script = f"{divert_postinst} && {replace_postinst}"
            cmd(["buildah", "run", self.cname, "--", "bash", "-c", postinst_script],
                check=False, env=env)
            # Run apt-get install with --allow-unauthenticated and --fix-missing
            # --fix-missing: skip packages that can't be fetched (e.g. 404 from broken repos)
            rc = cmd(["buildah", "run", "--env", "DEBIAN_FRONTEND=noninteractive",
                      self.cname, "--", "apt-get", "install", "-y",
                      "--no-install-recommends", "--allow-unauthenticated",
                      "--fix-missing",
                      "-o", 'Dpkg::Options::=--force-overwrite',
                      "-o", 'Dpkg::Options::=--force-confdef',
                      "-o", 'Dpkg::Options::=--force-confold'] + packages,
                     check=False, env=env)
            # Restore real lvm2 postinst script after install
            logging.info("Restoring real lvm2 postinst script")
            restore_postinst = "dpkg-divert --remove --rename /var/lib/dpkg/info/lvm2.postinst 2>/dev/null || true"
            cmd(["buildah", "run", self.cname, "--", "bash", "-c", restore_postinst],
                check=False, env=env)
            if rc != 0:
                logging.warn("apt-get install returned %d, attempting to fix broken packages", rc)
                # Retry install with --fix-broken to resolve partial installs
                rc2 = cmd(["buildah", "run", "--env", "DEBIAN_FRONTEND=noninteractive",
                           self.cname, "--", "apt-get", "install", "-y",
                           "--fix-broken", "--fix-missing",
                           "--no-install-recommends", "--allow-unauthenticated",
                           "-o", 'Dpkg::Options::=--force-overwrite',
                           "-o", 'Dpkg::Options::=--force-confdef',
                           "-o", 'Dpkg::Options::=--force-confold'],
                          check=False, env=env)
                if rc2 != 0:
                    logging.warn("apt-get --fix-broken returned %d, running dpkg --configure -a", rc2)
                    rc3 = cmd(["buildah", "run", "--env", "DEBIAN_FRONTEND=noninteractive",
                               self.cname, "--", "dpkg", "--configure", "-a",
                               "--force-overwrite", "--force-confdef", "--force-confold"],
                              check=False, env=env)
                    if rc3 != 0:
                        raise Exception("Installing base packages failed")
                # Verify requested packages were actually installed
                logging.info("Verifying requested packages were installed")
                verify_cmd = " && ".join([f"dpkg -s {pkg} >/dev/null 2>&1" for pkg in packages])
                rc_verify = cmd(["buildah", "run", self.cname, "--", "bash", "-c", verify_cmd],
                                check=False, env=env)
                if rc_verify != 0:
                    logging.error("Some requested packages were NOT installed after fix attempt")
                    # Log which packages are missing
                    for pkg in packages:
                        rc_pkg = cmd(["buildah", "run", self.cname, "--", "dpkg", "-s", pkg],
                                     check=False, env=env)
                        if rc_pkg != 0:
                            logging.error(f"MISSING package: {pkg}")
                    raise Exception("Installing base packages failed - required packages missing")
            return
        elif self.pkg_man == "apk":
            env = os.environ.copy()
            if proxy != "":
                env['http_proxy'] = proxy
                env['https_proxy'] = proxy
            
            args = [self.cname, '--', 'apk', 'add', '--root', self.mname, '--no-cache', '--no-verify']
            args.extend(packages)
            rc = cmd(["buildah","run"] + args, env=env)
            if rc != 0:
                raise Exception("Installing base packages failed")
            return

        rc = cmd([self.pkg_man] + args)
        if rc == 104:
            raise Exception("Installing base packages failed")

        if rc == 107:
            logging.warn("one or more RPM postscripts failed to run")

    def remove_base_packages(self, remove_packages):
        # check if there are packages to remove
        if remove_packages is None or len(remove_packages) == 0:
            logging.warn("REMOVE PACKAGES: no package passed to remove\n")
            return

        logging.info(f"REMOVE PACKAGES: removing these packages from container {self.cname}")
        logging.info("\n".join(remove_packages))
        for p in remove_packages:
            args = [self.cname, '--', 'rpm', '-e', '--nodeps', p]
            cmd(["buildah","run"] + args)

    def install_base_package_groups(self, package_groups, registry_loc, proxy):
        # check if there are packages groups to install
        if package_groups is None or len(package_groups) == 0:
            logging.warn("PACKAGE GROUPS: no package groups passed to install\n")
            return

        logging.info(f"PACKAGE GROUPS: Installing these package groups to {self.cname}")
        logging.info("\n".join(package_groups))
        args = []

        if self.pkg_man == "zypper":
            logging.warn("zypper does not support package groups")
        elif self.pkg_man == "dnf":
            helper = self.helper_cname if self.helper_cname else self.cname
            reposdir = os.path.join(self.mname, 'etc/yum.repos.d')
            dnf_run = [
                "buildah", "run",
                "--volume", f"{self.mname}:{self.mname}:z",
                helper, "--",
                "dnf", f"--installroot={self.mname}",
                f"--setopt=reposdir={reposdir}",
                "--setopt=logdir=/tmp",
                "--setopt=cachedir=/tmp/dnf-cache",
                "groupinstall", "-y", "--nogpgcheck"
            ]
            if proxy != "":
                dnf_run.extend([f'--setopt=proxy={proxy}'])
            dnf_run.extend(package_groups)
            rc = cmd(dnf_run)
            if rc == 104:
                raise Exception("Installing package groups failed")
        elif self.pkg_man == "apt":
            logging.warn("apt does not support package groups")
            return
        elif self.pkg_man == "apk":
            logging.warn("apk does not support package groups")
            return

    def install_base_modules(self, modules, registry_loc, proxy):
        # check if there are modules groups to install
        if modules is None or len(modules) == 0:
            logging.warn("PACKAGE MODULES: no modules passed to install\n")
            return
        logging.info(f"MODULES: Running these module commands for {self.cname}")
        for mod_cmd, mod_list in modules.items():
            logging.info(mod_cmd + ": " + " ".join(mod_list))
        for mod_cmd, mod_list in modules.items():
            args = []
            if self.pkg_man == "zypper":
                logging.warn("zypper does not support package groups")
                return
            elif self.pkg_man == "dnf":
                helper = self.helper_cname if self.helper_cname else self.cname
                reposdir = os.path.join(self.mname, 'etc/yum.repos.d')
                dnf_run = [
                    "buildah", "run",
                    "--volume", f"{self.mname}:{self.mname}:z",
                    helper, "--",
                    "dnf", f"--installroot={self.mname}",
                    f"--setopt=reposdir={reposdir}",
                    "--setopt=logdir=/tmp",
                    "--setopt=cachedir=/tmp/dnf-cache",
                    "module", mod_cmd, "-y", "--nogpgcheck"
                ]
                if proxy != "":
                    dnf_run.extend([f'--setopt=proxy={proxy}'])
                dnf_run.extend(mod_list)
                rc = cmd(dnf_run)
            elif self.pkg_man == "apt":
                logging.warn("apt does not support modules")
                return
            elif self.pkg_man == "apk":
                logging.warn("apk does not support modules")
                return
            if rc != 0:
                raise Exception("Failed to run module cmd", mod_cmd, ' '.join(mod_list))
            

    def install_base_commands(self, commands):
        # check if there are commands to install
        if commands is None or len(commands) == 0:
            logging.warn("COMMANDS: no commands passed to run\n")
            return

        logging.info(f"COMMANDS: running these commands in {self.cname}")
        for c in commands:
            logging.info(c['cmd'])
            build_cmd = ["buildah","run"]
            if 'buildah_extra_args' in c:
              build_cmd.extend(c['buildah_extra_args'])
            args = [self.cname, '--', 'bash', '-c', c['cmd']]
            if 'loglevel' in c:
                if c['loglevel'].upper() == "INFO":
                    loglevel = logging.info
                elif c['loglevel'].upper() == "WARN":
                    loglevel = logging.warn
                else:
                    loglevel = logging.error
            else:
                loglevel = logging.error
            out = cmd(build_cmd + args, stderr_handler=loglevel)

    def install_base_copyfiles(self, copyfiles):
        if copyfiles is None or len(copyfiles) == 0:
            logging.warn("COPYFILES: no files to copy\n")
            return
        logging.info(f"COPYFILES: copying these files to {self.cname}")
        for f in copyfiles:
            args = []
            if 'opts' in f:
                for o in f['opts']:
                    args.extend(o.split())
            logging.info(f['src'] + ' -> ' + f['dest'])
            args +=  [ self.cname, f['src'], f['dest'] ]
            out=cmd(["buildah","copy"] + args)
