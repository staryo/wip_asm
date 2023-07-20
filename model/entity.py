from collections import defaultdict


class Entity(object):
    def __init__(self, code, product, address):
        self.code = code
        self.product = product
        self.spec = {}
        self.back_spec = {}
        self.address = set()
        self.dept = None
        if address is not None:
            self.address.add(address)

    def add_spec(self, version_id):
        self.spec[version_id] = defaultdict(float)
        return self.spec[version_id]

    def get_spec(self, version, report=None, amount=1):
        if not report:
            report = defaultdict(float)
        for entity in self.spec[version.version_id]:
            if entity.product is None:
                continue
            elif entity.code == entity.product.code:
                report[entity] += self.spec[version.version_id][entity] * amount
            elif entity.code not in version.entities:
                continue
            else:
                report.update(entity.get_spec(
                    version,
                    report,
                    self.spec[version.version_id][entity] * amount
                ))
        return report

    def get_back_spec(self, report=None, amount=1):
        if not report:
            report = defaultdict(float)
        for entity in self.back_spec:
            if entity.product != self.product:
                continue
            for version in entity.spec:
                for child in entity.spec[version]:
                    if child.product == entity.product:
                        continue
                    report[child] += entity.spec[version][child] * amount
                break
            report.update(entity.get_back_spec(
                report,
                self.back_spec[entity] * amount
            ))
            # if entity.product is None:
            #     continue
            # elif entity.code == entity.product.code:
            #     report[entity] += self.back_spec[entity] * amount
            # else:
            #     report.update(entity.get_back_spec(
            #         report,
            #         self.back_spec[entity] * amount
            #     ))
        return report
