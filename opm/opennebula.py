import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ElementTree

from .vminfo import VmInfo

class OpenNebula:

    ENV_ONEXMLRPC="ONE_XMLRPC"

    ONE_COMMANDS=["oneuser", "onevm", "onetemplate"]

    @staticmethod
    def command_implicit_enter(name, *args):
        command = [name, *args]
        logging.debug("Command with implicit 'enter' on STDIN: {0}".format(command))
        try:
            result = subprocess.run(command, input=b"\n", stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except Exception as e:
            raise Exception("Error while running command {0} (reason : {1})".format(command, e))
        if result.returncode != 0:
            raise Exception("Error while running command {0} (return code : {1}, stdout: {2}, stderr: {3})".format(command, result.returncode, result.stdout, result.stderr))
        logging.debug("STDOUT: {0}".format(result.stdout))
        return result.stdout.decode()

    @staticmethod
    def command(name, *args):
        command = [name, *args]
        logging.debug("Command: {0}".format(command))
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except Exception as e:
            raise Exception("Error while running command {0} (reason : {1})".format(command, e))
        if result.returncode != 0:
            raise Exception("Error while running command {0} (return code : {1}, stdout: {2}, stderr: {3})".format(command, result.returncode, result.stdout, result.stderr))
        # logging.debug("STDOUT: {0}".format(result.stdout))
        return result.stdout.decode()

    @classmethod
    def verify_environment(cls):
        endpoint = os.environ.get(cls.ENV_ONEXMLRPC)
        if endpoint is None:
            raise Exception("Undefined environment variable {0}, define it with : export {0}=\"http://your_opennebula_host:2633/RPC2\"".format(cls.ENV_ONEXMLRPC))
        else:
            logging.info("Using {0}={1} to commicate with OpenNebula".format(cls.ENV_ONEXMLRPC, endpoint))

    @classmethod
    def verify_commands(cls):
        for command in cls.ONE_COMMANDS:
            retult = None
            try:
                result = subprocess.run([command, "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except Exception as e:
                raise Exception("Error while running command (reason : {0})".format(command, e))
            logging.debug("Command '{0}' found, returned {1}".format(command, result.returncode))

    def set_user_info(self):
        try:
            result = self.command("oneuser", "show", "--xml")
        except Exception as e:
            raise Exception("Error while running command, try to log in using `oneuser login your_user_name --force` first (reason : {0})".format(e))
        root = ElementTree.fromstring(result)
        # logging.debug("XML: {0}".format(ElementTree.tostring(root)))
        self.uid = int(root.find("ID").text)
        self.gid = int(root.find("GID").text)
        logging.info("User has a valid authorization token (uid={0} gid={0})".format(self.uid, self.gid))

    def vm_set_group(self, vm_info, group):
        logging.debug("Setting group {0} for vm : {1}".format(group, vm_info))
        try:
            result = self.command("onevm", "chgrp", str(vm_info.id), group)
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))

    def vm_set_permissions(self, vm_info, permissions):
        logging.debug("Setting permissions {0} for vm : {1}".format(permissions, vm_info))
        try:
            result = self.command("onevm", "chmod", str(vm_info.id), permissions)
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))

    def vm_list(self):
        vms = {}
        try:
            result = self.command("onevm", "list", "--xml")
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))
        root = ElementTree.fromstring(result)
        # logging.debug("XML: {0}".format(ElementTree.tostring(root)))
        for vm_elem in root.findall("VM"):
            vm = VmInfo.from_one_xml(vm_elem)
            vms[vm.name] = vm
        # logging.debug("VM list: {0}".format(vms))
        return vms

    def vm_create(self, vm_info):
        logging.debug("Creating vm: {0}".format(vm_info))
        args = ["--name", vm_info.name,
                "--hold", # in case one_template uses PXE implicitely
                "--cpu", str(vm_info.cpu),
                "--vcpu", str(vm_info.vcpu),
                "--memory", "{0}m".format(vm_info.mem_mb)]
        if vm_info.arch is not None:
            args.append("--arch")
            args.append(vm_info.arch)
        if vm_info.boot is not None:
            args.append("--boot")
            args.append(vm_info.boot)
        if len(vm_info.networks) > 0:
            args.append("--nic")
            args.append(",".join(vm_info.networks))
        if vm_info.disks is not None and len(vm_info.disks) > 0:
            args.append("--disk")
            args.append(",".join([ x.to_arg() for x in vm_info.disks]))
        try:
            if vm_info.one_template is None:
                result = self.command("onevm", "create", *args)
            else:
                logging.warning("Creation of VM {0} from a template might require a prompt. In that case, this tool chooses the default entry (ie simulates 'enter')")
                result = self.command_implicit_enter("onetemplate", "instantiate", *args, vm_info.one_template)
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))
        # store vm id number
        if vm_info.one_template is None:
            # onevm output
            r = r'^ID: (\d+)$'
        else:
            # onetemplate output
            r = r'VM ID: (\d+)\n'
        m = re.search(r, result)
        if not m:
            raise Exception("Could not detect VM id after creation")
        vm_info.id = int(m.group(1))
        # set group
        if vm_info.group is not None:
            self.vm_set_group(vm_info, vm_info.group)
        # permissions
        if vm_info.permissions is not None:
            self.vm_set_permissions(vm_info, vm_info.permissions)

    def vm_destroy(self, vm_info):
        logging.debug("Destroying vm: {0}".format(vm_info))
        try:
            result = self.command("onevm", "terminate", "--hard", str(vm_info.id))
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))

    def vm_resize(self, vm_info, cpu_percent=None, vcpu_count=None, mem_mb=None):
        logging.debug("Resizing vm : {0}".format(vm_info))
        # setup args
        args = []
        if cpu_percent is not None:
            args.append("--cpu")
            args.append(str(cpu_percent))
        if vcpu_count is not None:
            args.append("--vcpu")
            args.append(str(vcpu_count))
        if mem_mb is not None:
            args.append("--memory")
            args.append(str(mem_mb))
        # skip early if noop
        if len(args) == 0:
            logging.info("No difference in vcpu/cpu/mem detected, not resizing VM {0}".format(vm_info.id))
            return
        # enforce state requirements, see https://docs.opennebula.org/5.4/operation/references/vm_states.html
        if vm_info.state not in [2, 4, 5, 8, 9]:
            raise Exception("VM {0} is in a state ({1}) where its envelope cannot be modified".format(vm_info.id, vm_info.state))
        # actual resize operation
        try:
            result = self.command("onevm", "resize", *args, str(vm_info.id))
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))
        logging.info("Resizing VM {0} done".format(vm_info.id))

    def vm_synchronize(self, vm_info, differences):
        logging.debug("Synchronizing vm : {0}".format(vm_info))
        # group
        try:
            group = differences['group']
        except KeyError:
            group = None
        if group is not None:
            group = group[1]
            if group is not None:
                self.vm_set_group(vm_info, group)
        # permissions
        try:
            permissions = differences['permissions']
        except KeyError:
            permissions = None
        if permissions is not None:
            permissions = permissions[1]
            if permissions is not None:
                self.vm_set_permissions(vm_info, permissions)
        # resize
        cpu_percent = vcpu_count = mem_mb = None
        try:
            cpu_percent = differences['cpu_percent']
        except KeyError:
            cpu_percent = None
        if cpu_percent is not None:
            cpu_percent = cpu_percent[1]
        try:
            vcpu_count = differences['vcpu_count']
        except KeyError:
            vcpu_count = None
        if vcpu_count is not None:
            vcpu_count = vcpu_count[1]
        try:
            mem_mb = differences['mem_mb']
        except KeyError:
            mem_mb = None
        if mem_mb is not None:
            mem_mb = mem_mb[1]
        self.vm_resize(vm_info, cpu_percent, vcpu_count, mem_mb)
        # updating VM definition following resize
        if cpu_percent is not None:
            vm_info.cpu = cpu_percent
        if vcpu_count is not None:
            vm_info.vcpu = vcpu_count
        if mem_mb is not None:
            vm_info.mem_mb = mem_mb
        logging.debug("VM infos post resize {0}".format(vm_info))
        # disks
        try:
            disks = differences['disks']
        except KeyError:
            disks = None
        if disks is not None:
            logging.warning("Changing disk topology could lead to data loss, so this function is not implemented and modifications should be done manually")
        # networks
        try:
            networks = differences['networks']
        except KeyError:
            networks = None
        if networks is not None:
            logging.warning("Changing network topology could break the network configuration of the guest (lose mac/ip leases, change interface names) so this function is not implemented and modifications should be done by hand")

    def __init__(self):
        pass


