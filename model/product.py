import operator

from model.product_version import ProductVersion


class Product(object):
    def __init__(self, code, name, identity, draft):
        self.code = code
        self.name = name
        self.identity = identity
        # self.version[product_version] = version_priority
        self.versions = {}
        self.draft = draft

    def update(self, identity, name):
        self.draft = False
        self.identity = identity
        self.name = name

    def add_version(self, version_id, version_priority):
        if self.get_version_with_id(version_id) is None:
            self.versions[ProductVersion(version_id)] = version_priority
        return self.get_version_with_id(version_id)

    def get_version_with_id(self, version_id):
        for version in self.versions:
            if version.version_id == version_id:
                return version
        return None

    def get_highest_priority_version(self):
        return min(self.versions.items(), key=operator.itemgetter(1))[0]

    def get_main_spec(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_spec(version)

    def get_dept(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_dept(version)

    def get_last_dept(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_last_dept()

    def get_main_spec_for_1012(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_spec_for_1012(version)

    def get_main_spec_for_101(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if self.get_dept() not in [
            '1011', '1012', '0742', '1014', '1015', '1016', '1017', '1019'
        ]:
            return {}
        if root is None:
            return {}
        return root.get_spec(version)

    def get_item_one(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_item_one(version)

    def get_item_one_for_1012(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return {}
        return root.get_item_one_for_1012(version)

    def get_routes(self):
        report = {}
        for version, priority in sorted(
                self.versions.items(), key=lambda x: x[1]
        ):
            root = version.get_root_entity()
            if root is None:
                continue
            try:
                report[version.version_id] = root.get_route(version)
            except RecursionError:
                print('Зацикливание в спецификации на ДСЕ ',
                      self.code, self.name, version.version_id)
        return report

    def update_priority(self, version_id, version_priority):
        version = self.get_version_with_id(version_id)
        if version is not None:
            self.versions[
                self.get_version_with_id(version_id)
            ] = version_priority
        else:
            self.add_version(version_id, version_priority)

    def get_batch_size(self, max_time, skip):
        version = self.get_highest_priority_version()
        # if self.code == '000000108901905001':
        #     a = 1
        root = version.get_root_entity()
        if root is None:
            return None
        try:
            return root.get_batch_size(version, max_time, skip)
        except RecursionError:
            print('Зацикливание в спецификации на ДСЕ ',
                  self.code, self.name, version.version_id)

    def get_cycles(self):
        version = self.get_highest_priority_version()
        root = version.get_root_entity()
        if root is None:
            return None
        try:
            return root.get_cycle(version)
        except RecursionError:
            print('Зацикливание в спецификации на ДСЕ ',
                  self.code, self.name, version.version_id)

