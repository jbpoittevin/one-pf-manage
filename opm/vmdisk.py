import logging
#import xml.etree.ElementTree as ElementTree

class VmDisk:

    def __init__(self, image=None, size_mb=None, dev_prefix=None):
        self.image = image
        self.size_mb = size_mb
        self.dev_prefix = dev_prefix

    def __repr__(self):
        return "VmDisk(image={0}, size_mb={1}, dev_prefix={2})".format(self.image, self.size_mb, self.dev_prefix)

    def pretty_tostring(self):
        size = "default size"
        if self.size_mb:
            size = "size {0} Mbytes".format(self.size_mb)
        dev_prefix = "default dev_prefix"
        if self.dev_prefix:
            dev_prefix = "dev_prefix {0}".format(self.dev_prefix)
        return "image {0} of {1} with {2}".format(self.image, size, dev_prefix)

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
        try:
            self.dev_prefix = params['dev_prefix']
            # logging.debug("dev_prefix overridden to {0}".format(self.dev_prefix))
        except KeyError:
            pass
        # logging.debug("After override vm : {0}".format(self))

    def to_arg(self):
        if self.size_mb is None and self.dev_prefix is None:
            return self.image
        else:
            options = ""
            if self.size_mb:
                options = "{0}size={1}".format(options, self.size_mb)
            if self.dev_prefix:
                if options:
                    options = "{0}:".format(options)
                options = "{0}dev_prefix={1}".format(options, self.dev_prefix)
            return "{0}:{1}".format(self.image, options)

    @staticmethod
    def from_one_xml(disk_elem):
        # <DISK>
        #     <IMAGE><![CDATA[ttylinux]]></IMAGE>
        #     <SIZE><![CDATA[256]]></SIZE>
        #     <IMAGE_UNAME><![CDATA[serveradmin]]></IMAGE_UNAME>
        #     <DEV_PREFIX><![CDATA[256]]></DEV_PREFIX>
        disk = VmDisk()
        # logging.debug("Xml: {0}".format(ElementTree.tostring(disk_elem)))
        # extract image
        value = disk_elem.find("IMAGE")
        if value is not None:
            disk.image = value.text
        # extract owner in case the image is not ours
        value = disk_elem.find("IMAGE_UNAME")
        if value is not None:
            disk.image = "{0}[{1}]".format(value.text, disk.image)
        # extract size
        value = disk_elem.find("SIZE")
        if value is not None:
            disk.size_mb = int(value.text)
        # extract dev_prefix
        value = disk_elem.find("DEV_PREFIX")
        if value is not None:
            disk.dev_prefix = value.text
        # return constructed
        # logging.debug("Parsed: {0}".format(disk))
        return disk

    def __eq__(self, other):
        # logging.debug("Comparing {0} == {1}".format(self, other))
        # image must be defined
        if self.image is None or other.image is None:
            raise Exception("A disk must be based on an image")
        if self.image != other.image:
            return False
        if self.size_mb != other.size_mb:
            return False
        return self.dev_prefix == other.dev_prefix

    def __ne__(self, other):
        # logging.debug("Comparing {0} != {1}".format(self, other))
        return not self.__eq__(other)


