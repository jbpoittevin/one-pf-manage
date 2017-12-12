#!/usr/bin/env python3

import json
import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ElementTree


class VmDisk:

    def __init__(self, image=None, size_mb=None):
        self.image = image
        self.size_mb = size_mb

    def __repr__(self):
        return "VmDisk[image={0}, size_mb={1}]".format(self.image, self.size_mb)


    def pretty_tostring(self):
        if self.size_mb is None:
            return "image {0} of default size".format(self.image)
        else:
            return "image {0} of size {1} Mbytes".format(self.image, self.size_mb)

    def override_config(self, params):
        # logging.debug("Before override disk : {0}".format(self))
        # logging.debug("Overriding disk with : {0}".format(params))
        try:
            self.image = params['image']
            # logging.debug("image overridden to {0}".format(self.image))
        except KeyError:
            pass
        try:
            self.size_mb = params['size_mb']
            # logging.debug("size_mb overridden to {0}".format(self.size_mb))
        except KeyError:
            pass
        # logging.debug("After override vm : {0}".format(self))

    def to_arg(self):
        if self.size_mb is None:
            return self.image
        else:
            return "{0}:size_mb={1}".format(self.image, self.size_mb)

    @staticmethod
    def from_one_xml(disk_elem):
        # <DISK>
        #     <IMAGE><![CDATA[ttylinux]]></IMAGE>
        #     <SIZE><![CDATA[40]]></SIZE>
        disk = VmDisk()
        # logging.debug("Xml: {0}".format(ElementTree.tostring(disk_elem)))
        # extract image
        value = disk_elem.find("IMAGE")
        if value is not None:
            disk.image = value.text
        # extract cpu
        value = disk_elem.find("SIZE")
        if value is not None:
            disk.vcpu = int(value.text)
        # return cosntructed
        # logging.debug("Parsed: {0}".format(disk))
        return disk


class VmInfo:

    @staticmethod
    def from_one_xml(vm_elem):
        # <VM>
        #   <ID>10</ID>
        #   <NAME>test</NAME>
        #   <STATE>8</STATE>
        #   <TEMPLATE>
        #     <CPU><![CDATA[0.1]]></CPU>
        #     <DISK> *many*
        #       <IMAGE><![CDATA[ttylinux]]></IMAGE>
        #       <SIZE><![CDATA[40]]></SIZE>
        #     </DISK>
        #     <MEMORY><![CDATA[256]]></MEMORY>
        #     <NIC> *many*
        #       <NETWORK><![CDATA[cloud]]></NETWORK>
        #       <NIC_ID>0</NIC_ID>
        #     </NIC>
        #     <VCPU><![CDATA[1]]></VCPU>
        # </VM>
        vm = VmInfo()
        # logging.debug("Xml: {0}".format(ElementTree.tostring(vm_elem)))
        # extract name
        value = vm_elem.find("NAME")
        if value is not None:
            vm.name = value.text
        # extract cpu
        value = vm_elem.find("TEMPLATE/CPU")
        if value is not None:
            vm.cpu = float(value.text)
        # extract vcpu
        value = vm_elem.find("TEMPLATE/VCPU")
        if value is not None:
            vm.vcpu = int(value.text)
        else:
            vm.vcpu = 1
        # extract mem_mb
        value = vm_elem.find("TEMPLATE/MEMORY")
        if value is not None:
            vm.mem_mb = int(value.text)
        # extract networks
        value = vm_elem.findall("TEMPLATE/NIC")
        if value is not None:
            vm.networks = {}
            for nic_elem in value:
                name = nic_elem.find("NETWORK").text
                order = int(nic_elem.find("NIC_ID").text)
                vm.networks[order] = name
            vm.networks = [ vm.networks[key] for key in sorted(vm.networks.keys()) ]
        # extract disks
        value = vm_elem.findall("TEMPLATE/DISK")
        if value is not None:
            vm.disks = [ VmDisk.from_one_xml(x) for x in value ]
        # extract one_template
        vm.one_template = None
        # extract id
        value = vm_elem.find("ID")
        if value is not None:
            vm.id = int(value.text)
        # extract state
        value = vm_elem.find("STATE")
        if value is not None:
            vm.state = int(value.text)
        # return constructed
        logging.debug("Parsed: {0}".format(vm))
        return vm

    def __init__(self, name=None, cpu=None, vcpu=None, mem_mb=None, networks=None, disks=None, one_template=None, vm_id=None, state=None):
        # configuration
        self.name = name
        self.cpu = cpu
        self.vcpu = vcpu
        self.mem_mb = mem_mb
        self.networks = networks
        self.disks = disks
        self.one_template = one_template
        # state
        self.id = vm_id
        self.state = state

    def __repr__(self):
        return "VmInfo[name={0}, cpu={1}, vcpu={2}, mem_mb={3}, networks={4}, disks={5}, one_template={6}, id={7}, state={8}]".format(self.name, self.cpu, self.vcpu, self.mem_mb, self.networks, self.disks, self.one_template, self.id, self.state)

    def pretty_tostring(self):
        return "name: {0}\n\tcpu: {1}\n\tvcpu: {2}\n\tmem_mb: {3}\n\tone_template: {4}\n\tnetworks: {5}{6}\n\tdisks: {7}{8}".format(
            self.name, self.cpu, self.vcpu,
            self.mem_mb,
            self.one_template,
            len(self.networks),
            "".join([ "\n\t\t{0}".format(name) for name in self.networks]),
            len(self.disks),
            "".join([ "\n\t\t{0}".format(disk.pretty_tostring()) for disk in self.disks]))

    def override_config(self, params):
        # logging.debug("Before override vm : {0}".format(self))
        # logging.debug("Overriding vm with : {0}".format(params))
        try:
            self.cpu = params['cpu_percent']
            logging.debug("cpu overridden to {0}".format(self.cpu))
        except KeyError:
            pass
        try:
            self.vcpu = params['vcpu_count']
            logging.debug("vcpu overridden to {0}".format(self.vcpu))
        except KeyError:
            pass
        try:
            self.mem_mb = params['mem_mb']
            logging.debug("mem_mb overridden to {0}".format(self.mem_mb))
        except KeyError:
            pass
        try:
            self.networks = params['networks']
            logging.debug("networks overridden to {0}".format(self.networks))
        except KeyError:
            pass
        try:
            disk_overrides = params['disks']
            self.disks = []
            for disk_override in disk_overrides:
                disk = VmDisk()
                disk.override_config(disk_override)
                self.disks.append(disk)
            logging.debug("disks overridden to {0}".format(self.disks))
        except KeyError:
            pass
        try:
            self.one_template = params['one_template']
            logging.debug("one_template overridden to {0}".format(self.one_template))
        except KeyError:
            pass
        # logging.debug("After override vm : {0}".format(self))

    def compare_config_except_disks(self, target):
        differences = {}
        if self.cpu != target.cpu:
            differences['cpu'] = [self.cpu, target.cpu]
        if self.vcpu != target.vcpu:
            differences['vcpu'] = [self.vcpu, target.vcpu]
        if self.mem_mb != target.mem_mb:
            differences['mem_mb'] = [self.mem_mb, target.mem_mb]
        if self.networks != target.networks:
            differences['networks'] = [self.networks, target.networks]
        return differences


class OpenNebula:

    ENV_ONEXMLRPC="ONE_XMLRPC"

    ONE_COMMANDS=["oneuser", "onevm", "onetemplate"]

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
        if len(vm_info.networks) > 0:
            args.append("--nic")
            args.append(",".join(vm_info.networks))
        if len(vm_info.disks) > 0:
            args.append("--disk")
            args.append(",".join([ x.to_arg() for x in vm_info.disks]))
        try:
            result = self.command("onevm", "create", *args)
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))
        # store vm id number
        m = re.search(r'^ID: (\d+)$', result)
        if not m:
            raise Exception("Could not detect VM id after creation")
        vm_info.id = int(m.group(1))

    def vm_destroy(self, vm_info):
        logging.debug("Destroying vm: {0}".format(vm_info))
        try:
            result = self.command("onevm", "terminate", str(vm_info.id))
        except Exception as e:
            raise Exception("Error while running command (reason : {0})".format(e))

    def __init__(self):
        pass


class App:

    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.target = {}
        self.existing = {}
        self.one = OpenNebula()

    def setup_logging(self):
        # root logger
        numeric_level = getattr(logging, self.args.log_level.upper())
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        # format
        log_format = "%(message)s"
        if numeric_level == logging.DEBUG:
            log_format = " ".join([
                "thread=%(threadName)s",
                "module=%(module)s",
                "func=%(funcName)s",
                "line=%(lineno)d",
                ": {0}"]).format(log_format)
        # logging output
        handler = logging.StreamHandler()
        log_format = "%(asctime)s %(levelname)s {0}".format(log_format)
        # finalize
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        logging.debug("Command line arguments: {0}".format(args))

    def apply_class_recursive(self, jdata, vm, current_definition):
        try:
            vm_class = current_definition['class']
        except KeyError:
            vm_class = None
        # depth-first aplpication
        if vm_class is not None:
            self.apply_class_recursive(jdata, vm, jdata['classes'][vm_class])
        # apply provided overrides
        vm.override_config(current_definition)
        logging.debug("VM after class override {0}".format(vm))

    def load_v3(self, jdata):
        defs = {}
        self.platform_name = jdata['platform_name'].strip()
        if len(self.platform_name) == 0:
            raise Exception("Platform name cannot be empty, because every accessible OpenNebula VM would be considered part of the platform !")
        for vm_name, vm_host_def in jdata['hosts'].items():
            logging.debug("VM {0} definition {1}".format(vm_name, vm_host_def))
            # initialize vm data
            vm = VmInfo()
            vm.name = "{0}-{1}".format(self.platform_name, vm_name)
            # load default configuration
            try:
                defaults = jdata['defaults']
            except KeyError:
                defaults = None
            if defaults is not None:
                vm.override_config(defaults)
            logging.debug("VM after defaults {0}".format(vm))
            # apply overrides recursively by levels (hosts)
            self.apply_class_recursive(jdata, vm, vm_host_def)
            logging.debug("VM final configuration {0}".format(vm))
            # store final
            defs[vm.name] = vm
        logging.debug("VM definitions: {0}".format(defs))
        return defs

    def load(self, jsonfile):
        with open(self.args.jsonfile) as fileobj:
            j = json.load(fileobj)
            if int(j['format_version']) == 3:
                return self.load_v3(j)
            raise Exception("Unhandled format {0}".format(j['format_version']))

    def create(self, vm_name):
        logging.info("VM {0} does not exist, creating it".format(vm_name))
        vm = self.target[vm_name]
        self.one.vm_create(vm)
        logging.debug("Created VM with ID {0}".format(vm.id))
        print("{0}: created ID {1}".format(vm.name, vm.id))

    def verify(self, vm_name):
        logging.info("Verifying VM {0}".format(vm_name))
        current = self.existing[vm_name]
        target = self.target[vm_name]
        if current.name != target.name:
            raise Exception("Both VM do not refer to the same host")
        differences = current.compare_config_except_disks(target)
        if len(differences) > 0:
            delta = ", ".join([
                "existing {0} must change from {1} to {2}".format(key, change[0], change[1])
                for key, change in differences.items()
                ])
            print("{0}: ID {1}, {2}".format(vm_name, current.id, delta))

    def destroy(self, vm_name):
        logging.info("Destroying unreferenced VM {0}".format(vm_name))
        vm = self.existing[vm_name]
        self.one.vm_destroy(vm)
        logging.debug("Destroyed VM with ID {0}".format(vm.id))
        print("{0}: destroyed ID {1}".format(vm.name, vm.id))

    def list(self, platform_name):
        vms = self.one.vm_list()
        # ignoring VM without our prefix
        vms = {
            key:value for key, value in vms.items()
            if value.name.startswith("{0}-".format(platform_name))
        }
        logging.debug("Filtered VM {0}".format(vms))
        logging.info("Existing managed VM : {0}".format(", ".join(vms.keys()) if len(vms) > 0 else "None"))
        return vms

    def run(self):
        # parse data file
        self.target = self.load(args.jsonfile)
        # handle parse-only
        if self.args.action == "parse-only":
            for key in sorted(self.target):
                print(self.target[key].pretty_tostring())
            return
        # get existing vm FOR OUR PLATFORM
        OpenNebula.verify_environment()
        OpenNebula.verify_commands()
        self.one.set_user_info()
        self.existing = self.list(self.platform_name)
        # compute sets for actions
        current = set(self.existing.keys())
        target = set(self.target.keys())
        missing = target.difference(current)
        present = target.intersection(current)
        unreferenced = current.difference(target)
        if self.args.action == "status":
            for vm_name in sorted(missing):
                print("{0}: missing".format(self.target[vm_name].name))
            for vm_name in sorted(present):
                print("{0}: present ID {1}".format(self.existing[vm_name].name, self.existing[vm_name].id))
            for vm_name in sorted(unreferenced):
                print("{0}: unreferenced ID {1}".format(self.existing[vm_name].name, self.existing[vm_name].id))
        elif self.args.action == "create-missing":
            # create what must be created
            for vm_name in sorted(missing):
                self.create(vm_name)
        elif self.args.action == "verify-present":
            logging.warning("Due to differences in image naming and size between json file and opennebula xml, disks configuration verification is not yet implemented")
            # verify what could differ
            for vm_name in sorted(present):
                self.verify(vm_name)
        elif self.args.action == "delete-unreferenced":
            # delete what should not be there
            for vm_name in sorted(unreferenced):
                self.destroy(vm_name)
        elif self.args.action == "delete-all":
            # delete everything that exists related to our platform
            for vm_name in sorted(present):
                self.destroy(vm_name)


if __name__ == '__main__':

    import argparse
    import sys

    try:
        parser = argparse.ArgumentParser(description="one-pf-manage")
        parser.add_argument("-l", "--log-level", metavar="LVL", choices=["critical", "error", "warning", "info", "debug"], default="warning")
        parser.add_argument("jsonfile")
        parser.add_argument("action", nargs='?', choices=["status", "create-missing", "verify-present", "delete-unreferenced", "delete-all", "parse-only"], default="status")
        args = parser.parse_args()
        app = App(args)
        app.run()
        sys.exit(0)

    except KeyboardInterrupt as e:
        logging.warning("Caught SIGINT (Ctrl-C), exiting.")
        sys.exit(1)

    except SystemExit as e:
        message = "Exiting with return code {0}".format(e.code)
        if e.code == 0:
            logging.info(message)
        else:
            logging.warn(message)
            raise e

    except Exception as e:
        logging.critical("{0}: {1}".format(e.__class__.__name__, e))
        # when debugging, we want the stack-trace
        if args.log_level == "debug":
            raise e
