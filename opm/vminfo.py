import logging

from .vmdisk import VmDisk

class VmInfo:

    @staticmethod
    def from_one_xml(vm_elem):
        # <VM>
        #   <ID>10</ID>
        #   <GNAME>oneadmin</GNAME>
        #   <NAME>test</NAME>
        #   <PERMISSIONS>
        #     <OWNER_U>1</OWNER_U>
        #     <OWNER_M>1</OWNER_M>
        #     <OWNER_A>0</OWNER_A>
        #     <GROUP_U>0</GROUP_U>
        #     <GROUP_M>0</GROUP_M>
        #     <GROUP_A>0</GROUP_A>
        #     <OTHER_U>0</OTHER_U>
        #     <OTHER_M>0</OTHER_M>
        #     <OTHER_A>0</OTHER_A>
        #   </PERMISSIONS>
        #   <STATE>8</STATE>
        #   <TEMPLATE>
        #     <CPU><![CDATA[0.1]]></CPU>
        #     <DISK> *many*
        #       <IMAGE><![CDATA[ttylinux]]></IMAGE>
        #       <SIZE><![CDATA[40]]></SIZE>
        #       <DEV_PREFIX><![CDATA[256]]></DEV_PREFIX>
        #     </DISK>
        #     <MEMORY><![CDATA[256]]></MEMORY>
        #     <NIC> *many*
        #       <NETWORK><![CDATA[cloud]]></NETWORK>
        #       <NETWORK_UNAME><![CDATA[serveradmin]]></NETWORK_UNAME> *optional*
        #       <NIC_ID>0</NIC_ID>
        #     </NIC>
        #     <VCPU><![CDATA[1]]></VCPU>
        #     <OS>
        #       <ARCH><![CDATA[256]]></ARCH>
        #       <BOOT><![CDATA[256]]></BOOT>
        #     </OS>
        # </VM>
        vm = VmInfo()
        # logging.debug("Xml: {0}".format(ElementTree.tostring(vm_elem)))
        # extract name
        value = vm_elem.find("NAME")
        if value is not None:
            vm.name = value.text
        # extract group
        value = vm_elem.find("GNAME")
        if value is not None:
            vm.group = value.text
        # extract permissions
        value = vm_elem.find("PERMISSIONS")
        if value is not None:
            u_u = int(value.find("OWNER_U").text)
            u_m = int(value.find("OWNER_M").text)
            u_a = int(value.find("OWNER_A").text)
            g_u = int(value.find("GROUP_U").text)
            g_m = int(value.find("GROUP_M").text)
            g_a = int(value.find("GROUP_A").text)
            o_u = int(value.find("OTHER_U").text)
            o_m = int(value.find("OTHER_M").text)
            o_a = int(value.find("OTHER_A").text)
            vm.permissions = "{0}{1}{2}".format(
                u_u * 4 + u_m * 2 + u_a,
                g_u * 4 + g_m * 2 + g_a,
                o_u * 4 + o_m * 2 + o_a)
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
        # extract arch
        value = vm_elem.find("TEMPLATE/OS/ARCH")
        if value is not None:
            vm.arch = value.text
        # extract boot
        value = vm_elem.find("TEMPLATE/OS/BOOT")
        if value is not None:
            vm.boot = value.text
        # extract networks
        value = vm_elem.findall("TEMPLATE/NIC")
        if value is not None:
            vm.networks = {}
            for nic_elem in value:
                name = nic_elem.find("NETWORK").text
                order = int(nic_elem.find("NIC_ID").text)
                # extract owner in case the image is not ours
                owner = nic_elem.find("NETWORK_UNAME")
                if owner is not None:
                    name = "{0}[{1}]".format(owner.text, name)
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

    def __init__(self, name=None, cpu=None, vcpu=None, mem_mb=None, arch=None, boot=None, networks=None, disks=None, one_template=None, group=None, permissions=None, vm_id=None, state=None):
        # configuration
        self.name = name
        self.cpu = cpu
        self.vcpu = vcpu
        self.mem_mb = mem_mb
        self.arch = arch
        self.boot = boot
        self.networks = networks
        self.disks = disks
        self.one_template = one_template
        self.group = group
        self.permissions = permissions
        # state
        self.id = vm_id
        self.state = state

    def __repr__(self):
        return "VmInfo(name={0}, cpu={1}, vcpu={2}, mem_mb={3}, arch={4}, boot={5}, networks={6}, disks={7}, one_template={8}, group={9}, permissions={10}, id={11}, state={12})".format(self.name, self.cpu, self.vcpu, self.mem_mb, self.arch, self.boot, self.networks, self.disks, self.one_template, self.group, self.permissions, self.id, self.state)

    def pretty_tostring(self):
        disks = self.disks
        if disks is None:
            disks = []
        return "name: {0}\n\tgroup: {1}\n\tpermissions: {2}\n\tcpu: {3}\n\tvcpu: {4}\n\tmem_mb: {5}\n\tarch: {6}\n\tboot: {7}\n\tone_template: {8}\n\tnetworks: {9}{10}\n\tdisks: {11}{12}".format(
            self.name,
            self.group,
            self.permissions,
            self.cpu,
            self.vcpu,
            self.mem_mb,
            self.arch,
            self.boot,
            self.one_template,
            len(self.networks),
            "".join([ "\n\t\t{0}".format(name) for name in self.networks]),
            len(disks),
            "".join([ "\n\t\t{0}".format(disk.pretty_tostring()) for disk in disks]))

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
            self.arch = params['arch']
            logging.debug("arch overridden to {0}".format(self.arch))
        except KeyError:
            pass
        try:
            self.boot = params['boot']
            logging.debug("boot overridden to {0}".format(self.boot))
        except KeyError:
            pass
        try:
            self.networks = params['networks']
            logging.debug("networks overridden to {0}".format(self.networks))
        except KeyError:
            pass
        try:
            disk_overrides = params['disks']
            if disk_overrides is None:
                self.disks = None
            else:
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
        try:
            self.group = params['group']
            logging.debug("group overridden to {0}".format(self.group))
        except KeyError:
            pass
        try:
            self.permissions = params['permissions']
            logging.debug("permissions overridden to {0}".format(self.permissions))
        except KeyError:
            pass
        # logging.debug("After override vm : {0}".format(self))

    def compare_config(self, target):
        differences = {}
        if self.group is not None and target.group is not None and self.group != target.group:
            differences['group'] = [self.group, target.group]
        if self.permissions is not None and target.permissions is not None and self.permissions != target.permissions:
            differences['permissions'] = [self.permissions, target.permissions]
        if self.cpu != target.cpu:
            differences['cpu_percent'] = [self.cpu, target.cpu]
        if self.vcpu != target.vcpu:
            differences['vcpu_count'] = [self.vcpu, target.vcpu]
        if self.mem_mb != target.mem_mb:
            differences['mem_mb'] = [self.mem_mb, target.mem_mb]
        if self.arch != target.arch:
            differences['arch'] = [self.arch, target.arch]
        if self.boot != target.boot:
            differences['boot'] = [self.boot, target.boot]
        if self.networks != target.networks:
            differences['networks'] = [self.networks, target.networks]
        if self.disks is not None and target.disks is not None and len(self.disks) != len(target.disks):
            differences['disks'] = [self.disks, target.disks]
        else:
            if self.disks is not None and target.disks is not None:
                for x in range(len(self.disks)):
                    if self.disks[x] != target.disks[x]:
                        differences['disks'] = [self.disks, target.disks]
                        break
        return differences


