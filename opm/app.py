import json
import logging
import re

from .opennebula import OpenNebula
from .vminfo import VmInfo

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
        logging.debug("Command line arguments: {0}".format(self.args))

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

    def load_v4(self, jdata):
        defs = {}
        self.platform_name = jdata['platform_name'].strip()
        self.platform_is_domain = jdata.get('platform_is_domain', False)
        if len(self.platform_name) == 0:
            raise Exception("Platform name cannot be empty, because every"
                " accessible OpenNebula VM would be considered part of the"
                " platform !")
        for vm_name, vm_host_def in jdata['hosts'].items():
            logging.debug("VM {0} definition {1}".format(vm_name, vm_host_def))
            # initialize vm data
            vm = VmInfo()
            if self.platform_is_domain:
                vm.name = "{}.{}".format(vm_name, self.platform_name)
            else:
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
        with open(jsonfile) as fileobj:
            j = json.load(fileobj)
            if int(j['format_version']) == 4:
                return self.load_v4(j)
            raise Exception("Unhandled format {0}".format(j['format_version']))

    def create(self, vm_name):
        logging.info("VM {0} does not exist, creating it".format(vm_name))
        vm = self.target[vm_name]
        self.one.vm_create(vm)
        logging.debug("Created VM with ID {0}".format(vm.id))
        print("{0}: created ID {1}".format(vm.name, vm.id))

    def synchronize(self, vm_name):
        logging.info("Synchronizing VM {0}".format(vm_name))
        current = self.existing[vm_name]
        target = self.target[vm_name]
        if current.name != target.name:
            raise Exception("Both VM do not refer to the same host")
        differences = current.compare_config(target)
        if len(differences) > 0:
            delta = ", ".join([
                "changing {0} from {1} to {2}".format(key, change[0], change[1])
                for key, change in differences.items()
                ])
            print("{0}: ID {1}, {2}".format(vm_name, current.id, delta))
            self.one.vm_synchronize(current, differences)

    def destroy(self, vm_name):
        logging.info("Destroying unreferenced VM {0}".format(vm_name))
        vm = self.existing[vm_name]
        self.one.vm_destroy(vm)
        logging.debug("Destroyed VM with ID {0}".format(vm.id))
        print("{0}: destroyed ID {1}".format(vm.name, vm.id))

    def list(self, platform_name):
        vms = self.one.vm_list()
        # ignoring VM without our prefix
        if self.platform_is_domain:
            pattern = r'.*\.{}'.format(platform_name)
        else:
            pattern = r'{}-.*'.format(platform_name)
        vms = {
            key:value for key, value in vms.items()
            if re.match(pattern, value.name)
        }
        logging.debug("Filtered VM {0}".format(vms))
        logging.info("Existing managed VM : {0}".format(", ".join(vms.keys()) if len(vms) > 0 else "None"))
        return vms

    def run_all(self):
        # parse data file
        for json_file in self.args.jsonfile:
            logging.info("Processing definition file: {0}".format(json_file))
            self.target = self.load(json_file)
            self.run()

    def run(self):
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
        elif self.args.action == "synchronize":
            # synchronize what could differ
            for vm_name in sorted(present):
                self.synchronize(vm_name)
        elif self.args.action == "delete-unreferenced":
            # delete what should not be there
            for vm_name in sorted(unreferenced):
                self.destroy(vm_name)
        elif self.args.action == "delete-all":
            # delete everything that exists related to our platform
            for vm_name in sorted(present):
                self.destroy(vm_name)


