"""Image build installer — manages repos, packages, and commands for container images."""

import logging
import os
import tempfile

import pathmod
# Written Modules
from utils import cmd


class Installer:
    """Manages package installation for container image builds."""

    def __init__(self, pkg_man, cname, mname):
        self.pkg_man = pkg_man
        self.cname = cname
        self.mname = mname

        # Create temporary directory for logs, cache, etc. for package manager
        os.makedirs(os.path.join(mname, "tmp"), exist_ok=True)
        self.tdir = tempfile.mkdtemp(prefix="image-build-")
        logging.info(
            'Installer: Temporary directory for %s created at %s',
            self.pkg_man, self.tdir,
        )

        if pkg_man == "dnf":
            # DNF complains if the log directory is not present
            os.makedirs(os.path.join(self.tdir, "dnf/log"))

    def _install_zypper_repo(self, repo, repo_dest):
        """Install a single repo via zypper addrepo."""
        args = [
            "-D", os.path.join(self.mname, pathmod.sep_strip(repo_dest)),
            "addrepo", "-f", "-p",
        ]
        # Use priority only when explicitly provided and non-empty; default to 99
        _zyp_priority = str(repo.get('priority', '') or '').strip()
        args.append(_zyp_priority if _zyp_priority else '99')
        args.append(repo['url'])
        args.append(repo['alias'])

        rc = cmd([self.pkg_man] + args)
        if rc != 0:
            raise RuntimeError(
                "Failed to install repo %s %s" % (repo['alias'], repo['url'])
            )

    def _install_dnf_repo(self, repo, repo_dest, proxy):
        """Write a .repo file directly for DNF with priority support.

        Priority key is optional in repo_status.yml:
          - key absent or empty -> default 99
          - key present with value -> use that value
        """
        repo_dir = os.path.join(self.mname, pathmod.sep_strip(repo_dest))
        os.makedirs(repo_dir, exist_ok=True)

        repo_id = repo['alias']
        repo_file_path = os.path.join(repo_dir, repo_id + '.repo')
        _raw_priority = str(repo.get('priority', '') or '').strip()
        priority_val = _raw_priority if _raw_priority else '99'

        repo_content = "[%s]\n" % repo_id
        repo_content += "name=added from: %s\n" % repo['url']
        repo_content += "baseurl=%s\n" % repo['url']
        repo_content += "enabled=1\n"
        repo_content += "gpgcheck=0\n"
        repo_content += "sslverify=0\n"
        repo_content += "priority=%s\n" % priority_val
        if proxy != "":
            repo_content += "proxy=%s\n" % proxy

        with open(repo_file_path, 'w', encoding='utf-8') as rf:
            rf.write(repo_content)
        logging.info(
            "Created repo file: %s (priority=%s)", repo_file_path, priority_val,
        )

    def install_repos(self, repos, repo_dest, proxy):
        """Install repository definitions on the target image.

        Args:
            repos: List of repo dicts with alias, url, and optional gpg/priority.
            repo_dest: Destination path for repo files inside the image.
            proxy: Proxy URL string (empty string if none).
        """
        # check if there are repos passed for install
        if len(repos) == 0:
            logging.info("REPOS: no repos passed to install\n")
            return

        logging.info("REPOS: Installing these repos to %s", self.cname)
        for r in repos:
            logging.info(r['alias'] + ': ' + r['url'])
            if self.pkg_man == "zypper":
                self._install_zypper_repo(r, repo_dest)
            elif self.pkg_man == "dnf":
                self._install_dnf_repo(r, repo_dest, proxy)

            if "gpg" in r:
                # Using rpm apparently works for both Yum- and Zypper-based distros.
                args = []
                if proxy != "":
                    _arg_env = os.environ.copy()
                    _arg_env['https_proxy'] = proxy
                args.append("--root="+self.mname)
                args.append("--import")
                args.append(r["gpg"])

                rc = cmd(["rpm"] + args)
                if rc != 0:
                    raise RuntimeError(
                        "Failed to install gpg key for %s at URL %s"
                        % (r['alias'], r['gpg'])
                    )

    def install_base_packages(self, packages, registry_loc, proxy):
        """Install base RPM packages into the container image.

        Args:
            packages: List of package names to install.
            registry_loc: Path to repo directory inside the image.
            proxy: Proxy URL string (empty string if none).
        """
        # check if there are packages to install
        if len(packages) == 0:
            logging.warning("PACKAGES: no packages passed to install\n")
            return

        logging.info("PACKAGES: Installing these packages to %s", self.cname)
        logging.info("\n".join(packages))

        args = []
        if self.pkg_man == "zypper":
            args.extend([
                "-n", "-D",
                os.path.join(self.mname, pathmod.sep_strip(registry_loc)),
                "-C", self.tdir,
                "--no-gpg-checks", "--installroot", self.mname,
                "install", "-l",
            ])
            args.extend(packages)
        elif self.pkg_man == "dnf":
            reposdir = os.path.join(
                self.mname, pathmod.sep_strip(registry_loc),
            )
            logdir = os.path.join(self.tdir, self.pkg_man, "log")
            cachedir = os.path.join(self.tdir, self.pkg_man, "cache")
            args.extend([
                "--setopt=reposdir=" + reposdir,
                "--setopt=logdir=" + logdir,
                "--setopt=cachedir=" + cachedir,
            ])
            if proxy != "":
                args.append("--setopt=proxy="+proxy)
            args.extend([
                "install", "-y", "--nogpgcheck",
                "--installroot", self.mname,
            ])
            args.extend(packages)

        rc = cmd([self.pkg_man] + args)
        if rc == 104:
            raise RuntimeError("Installing base packages failed")

        if rc == 107:
            logging.warning("one or more RPM postscripts failed to run")

    def remove_base_packages(self, remove_packages):
        """Remove packages from the container image via rpm --nodeps.

        Args:
            remove_packages: List of package names to remove.
        """
        # check if there are packages to remove
        if len(remove_packages) == 0:
            logging.warning("REMOVE PACKAGES: no package passed to remove\n")
            return

        logging.info(
            "REMOVE PACKAGES: removing these packages from container %s",
            self.cname,
        )
        logging.info("\n".join(remove_packages))
        for p in remove_packages:
            args = [self.cname, '--', 'rpm', '-e', '--nodeps', p]
            cmd(["buildah","run"] + args)

    def install_base_package_groups(self, package_groups, registry_loc, proxy):
        """Install package groups (e.g., dnf groupinstall) into the image.

        Args:
            package_groups: List of group names.
            registry_loc: Path to repo directory inside the image.
            proxy: Proxy URL string (empty string if none).
        """
        # check if there are packages groups to install
        if len(package_groups) == 0:
            logging.warning(
                "PACKAGE GROUPS: no package groups passed to install\n",
            )
            return

        logging.info(
            "PACKAGE GROUPS: Installing these package groups to %s",
            self.cname,
        )
        logging.info("\n".join(package_groups))
        args = []

        if self.pkg_man == "zypper":
            logging.warning("zypper does not support package groups")
        elif self.pkg_man == "dnf":
            reposdir = os.path.join(
                self.mname, pathmod.sep_strip(registry_loc),
            )
            logdir = os.path.join(self.tdir, self.pkg_man, "log")
            cachedir = os.path.join(self.tdir, self.pkg_man, "cache")
            args.extend([
                "--setopt=reposdir=" + reposdir,
                "--setopt=logdir=" + logdir,
                "--setopt=cachedir=" + cachedir,
            ])
            if proxy != "":
                args.append("--setopt=proxy="+proxy)
            args.extend([
                "groupinstall", "-y", "--nogpgcheck",
                "--installroot", self.mname,
            ])
            args.extend(package_groups)

        rc = cmd([self.pkg_man] + args)
        if rc == 104:
            raise RuntimeError("Installing base packages failed")

    def install_base_modules(self, modules, registry_loc, proxy):
        """Install DNF modules (e.g., module enable/install) into the image.

        Args:
            modules: Dict mapping module commands to lists of module specs.
            registry_loc: Path to repo directory inside the image.
            proxy: Proxy URL string (empty string if none).
        """
        # check if there are modules groups to install
        if len(modules) == 0:
            logging.warning("PACKAGE MODULES: no modules passed to install\n")
            return
        logging.info("MODULES: Running these module commands for %s", self.cname)
        for mod_cmd, mod_list in modules.items():
            logging.info("%s: %s", mod_cmd, " ".join(mod_list))
        for mod_cmd, mod_list in modules.items():
            args = []
            if self.pkg_man == "zypper":
                logging.warning("zypper does not support package groups")
                return
            if self.pkg_man == "dnf":
                reposdir = os.path.join(
                    self.mname, pathmod.sep_strip(registry_loc),
                )
                logdir = os.path.join(self.tdir, self.pkg_man, "log")
                cachedir = os.path.join(self.tdir, self.pkg_man, "cache")
                args.extend([
                    "--setopt=reposdir=" + reposdir,
                    "--setopt=logdir=" + logdir,
                    "--setopt=cachedir=" + cachedir,
                ])
                if proxy != "":
                    args.append("--setopt=proxy="+proxy)
                args.extend([
                    "module", mod_cmd, "-y",
                    "--nogpgcheck", "--installroot", self.mname,
                ])
                args.extend(mod_list)
            rc = cmd([self.pkg_man] + args)
            if rc != 0:
                raise RuntimeError(
                    "Failed to run module cmd %s %s"
                    % (mod_cmd, ' '.join(mod_list))
                )

    def install_base_commands(self, commands):
        """Run arbitrary commands inside the container via buildah run.

        Args:
            commands: List of command dicts with cmd, optional loglevel,
                      and optional buildah_extra_args.
        """
        # check if there are commands to install
        if len(commands) == 0:
            logging.warning("COMMANDS: no commands passed to run\n")
            return

        logging.info("COMMANDS: running these commands in %s", self.cname)
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
                    loglevel = logging.warning
                else:
                    loglevel = logging.error
            else:
                loglevel = logging.error
            cmd(build_cmd + args, stderr_handler=loglevel)

    def install_base_copyfiles(self, copyfiles):
        """Copy files into the container image via buildah copy.

        Args:
            copyfiles: List of dicts with src, dest, and optional opts.
        """
        if len(copyfiles) == 0:
            logging.warning("COPYFILES: no files to copy\n")
            return
        logging.info("COPYFILES: copying these files to %s", self.cname)
        for f in copyfiles:
            args = []
            if 'opts' in f:
                for o in f['opts']:
                    args.extend(o.split())
            logging.info(f['src'] + ' -> ' + f['dest'])
            args += [self.cname, f['src'], f['dest']]
            cmd(["buildah","copy"] + args)
