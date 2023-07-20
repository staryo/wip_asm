class ProductVersion(object):
    def __init__(self, version_id):
        self.version_id = version_id
        # self.entities[code] = entity
        self.entities = {}

    def get_root_entity(self):
        for entity in self.entities.values():
            if entity.code == entity.product.code:
                return entity
        return None
