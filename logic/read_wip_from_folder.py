import os
import sys
from xml.etree.ElementTree import ParseError, XMLParser
from xml.etree.ElementTree import parse

from tqdm import tqdm

from logic.xml_tools import get_text_value, get_float_value, \
    get_float_value_with_dot
from model.entity import Entity
from model.product import Product
from model.special_item_one import SpecialItemOne


class ReadSession(object):
    def __init__(self):
        self.entities = {}
        self.products = {}
        self.item_one_entities = {}

    def add_product(self, code, identity, name, draft):
        product_code = code.zfill(18)
        if product_code not in self.products:
            self.products[product_code] = Product(
                code=product_code,
                identity=identity,
                name=name,
                draft=draft
            )
        if not draft and self.products[product_code].draft:
            self.products[product_code].update(
                identity=identity,
                name=name
            )
        return self.products[product_code]

    def add_entity(self, code, identity, name, product_code,
                   version_id, version_priority, address, draft=False):
        if not draft:
            if code == product_code:
                product = self.add_product(product_code, identity,
                                           name, draft=False)
                product.update_priority(version_id, version_priority)
            else:
                product = self.add_product(product_code, None,
                                           None, draft=True)
            version = product.add_version(version_id, version_priority)
        else:
            product = None
            version = None
        code = code.zfill(18)
        if code not in self.entities:
            self.entities[code] = Entity(
                code=code,
                product=product,
                address=address
            )
        if address is not None:
            self.entities[code].address.add(address)
        if not draft:
            self.entities[code].product = product
            version.entities[code] = self.entities[code]
            self.entities[code].add_spec(version.version_id)
        return self.entities[code]

    def add_item_one(self, parent, base_code, child, amount, address):
        code = '{}({})'.format(
            base_code,
            parent.code,
        )
        entity = self.item_one_entities.get(code)
        base_item = self.add_entity(
            code=base_code,
            identity=None,
            name=None,
            product_code=None,
            version_id=None,
            version_priority=None,
            address=address,
            draft=True
        )
        if entity is None:
            entity = self.item_one_entities[code] = SpecialItemOne(
                code=code,
                base_item=base_item,
            )
        entity.spec[child] += amount
        return entity

    def read_from_folder(self, path, pattern, backup_path=None):
        list_of_files = os.listdir(path)
        # Iterate over all the entries
        if len(list_of_files) > 100:
            iter = tqdm(sorted(list_of_files), desc=path, file=sys.stdout)
        else:
            iter = sorted(list_of_files)

        for entry in iter:
            # Create full path
            full_path = os.path.join(path, entry)
            # If entry is a directory then get the list
            # of files in this directory
            if os.path.isdir(full_path):
                self.read_from_folder(full_path, pattern, backup_path)
            else:
                if pattern in entry:
                    # tqdm.write(full_path)
                    with open(full_path, mode='r', encoding='utf-8') as file:
                        answer = self.read_from_file(file, backup_path)
                        if answer == {}:
                            tqdm.write(full_path)

    def read_from_file(self, xml_file, backup_path):
        # парсим xml
        try:
            # ставим utf-8 хардкодом, чтоб никаких неожиданностей не было
            xmlp = XMLParser(encoding="utf-8")
            tree = parse(xml_file, parser=xmlp)
            root = tree.getroot()
        except ParseError:
            tqdm.write('Ошибка чтения файла -- не распознан корень')
            return {}

        report = {'result': 'good'}

        # ищем
        material = root.find('MATERIALDATA')
        if material is None:
            tqdm.write('Ошибка чтения файла -- не распознан MATERIALDATA')
            return {}
        version_id = get_text_value(material, 'VERID')
        if version_id is None:
            tqdm.write(('Ошибка чтения файла -- не распознан VERID. Материал {}').format(
                get_text_value(material, 'MATNR')
            ))
            version_id = 'FICT'
            # return {}
        # это я закидываю все xml в свою базу XML-ек
        # уникальным является сочетание MATNR и VERID
        # if '1354C0000007' in get_text_value(material, 'MATNR'):
        #     tqdm.write('{} {} {}'.format(
        #         # full_path,
        #         get_text_value(material, 'MATNR'),
        #         version_id,
        #         get_float_value(material, 'PRIORITY')
        #     ))
        #     a=1
        # if get_text_value(material, 'STATUS') == 'Z4':
        #     tqdm.write(('Ошибка чтения файла -- статут Z4. Материал {}').format(
        #         get_text_value(material, 'MATNR')
        #     ))
        #     return {}
        if backup_path:
            tree.write(os.path.join(backup_path, '{}_{}'.format(
                get_text_value(material, 'MATNR'),
                version_id
            )), encoding='UTF-8')
            return report

        # if '108900900081-A0121' in get_text_value(material, 'MATNR'):
        #     a=1
        if get_text_value(material, 'MATNR') is None:
            tqdm.write('ALARM')
        # tqdm.write('{} ==> {}'.format(
        #     get_text_value(material, 'MATNR'),
        #     get_text_value(material, 'MAKTX')
        # ))


        try:
            priority = get_float_value(material, 'PRIORITY')
        except AttributeError:
            priority = 999

        if version_id == 'FICT':
            priority = 999

        name = get_text_value(material, 'MAKTX')
        if name == '':
            name = '-'

        product_code = get_text_value(material, 'PRODUCT')
        for item in SPECIAL_ITEMS:
            if item in get_text_value(material, 'MATNR'):
                product_code = get_text_value(material, 'MATNR').zfill(18)
                break

        parent = self.add_entity(
            code=get_text_value(material, 'MATNR').zfill(18),
            identity=get_text_value(material, 'MEINS'),
            name=name,
            product_code=product_code,
            version_id=version_id,
            version_priority=priority,
            address=None
        )

        bom = root.find('BOMDATA')
        if bom:
            bom_items = bom.findall('BOMITEM')
            base_quantity = get_float_value(bom.find('BOMHEADER'), 'BASE_QUAN')
            dept = None
            items = set()
            for item in bom_items:
                if get_text_value(item, 'AI_GROUP') is not None:
                    if get_float_value(item, 'USAGE_PROB') == 0:
                        continue
                if get_text_value(item, 'ISSUE_LOC') is not None:
                    dept = get_text_value(item, 'ISSUE_LOC')
                    if dept == '103B':
                        dept = '1054'
                    if parent.dept is None:
                        parent.dept = dept
                if get_text_value(item, 'ITEM_CATEG') in ['Y']:
                    continue
                if get_text_value(item, 'ITEM_CATEG') in ['X']:
                    if get_text_value(item, 'COMPONENT') in items:
                        tqdm.write(
                            'Дубль номенклатуры {} в спецификации {}'.format(
                                get_text_value(item, 'COMPONENT'),
                                get_text_value(material, 'MATNR')
                            ))
                    else:
                        items.add(get_text_value(item, 'COMPONENT'))
                if get_text_value(item, 'ITEM_CATEG') in ['O', 'U', 'Y']:
                    child = self.add_entity(
                        code=get_text_value(item, 'COMPONENT'),
                        identity=get_text_value(item, 'COMP_UNIT'),
                        name='[{}]{}'.format(
                            get_text_value(item, 'ITEM_CATEG'),
                            get_text_value(item, 'MAKTX'),
                        ),
                        product_code=get_text_value(item, 'COMPONENT'),
                        version_id='MAIN',
                        version_priority=0,
                        address=get_text_value(item, 'ISSUE_LOC'),
                        draft=False
                    )
                else:
                    child = self.add_entity(
                        code=get_text_value(item, 'COMPONENT'),
                        identity=None,
                        name=None,
                        product_code=None,
                        version_id=None,
                        version_priority=None,
                        address=get_text_value(item, 'ISSUE_LOC'),
                        draft=True
                    )
                try:
                    if get_text_value(item, 'ITEM_CATEG') != '1':
                        parent.spec[version_id][child] = get_float_value_with_dot(
                            item, 'COMP_QTY'
                        ) / base_quantity
                        continue
                except ValueError:
                    tqdm.write(
                        'Ошибка чтения количества в спецификации, '
                        'PARENT {}, CHILD {}'.format(
                            parent.code, child.code
                        )
                    )
                    continue

                if get_text_value(item, 'ZBOM_KAU') is None:
                    continue
                item_one_entity = self.add_item_one(
                    parent=parent,
                    base_code=get_text_value(item, 'ZBOM_KAU'),
                    child=child,
                    amount=get_float_value_with_dot(
                        item, 'COMP_QTY'
                    ) / base_quantity,
                    address=get_text_value(item, 'ISSUE_LOC')
                )
                parent.item_one[version_id].append(item_one_entity)

        route = root.find('ROUTINGDATA')
        if '000000009618646051' in get_text_value(material, 'MATNR'):
            a = 1
        if route:
            route_operations = route.findall('ROUTINGOPERATION')
            for operation in route_operations:
                if '9990' in get_text_value(operation, 'VORNR'):
                    parent.add_operation(
                        version_id=version_id,
                        operation_id='{}_{}_{}ц'.format(
                            get_text_value(material, 'MATNR'),
                            version_id,
                            get_text_value(operation, 'VORNR')
                        ),
                        equipment=get_text_value(operation, 'ARBID'),
                        department=dept,
                        nop=get_text_value(operation, 'VORNR'),
                        name=get_text_value(operation, 'LTXA1'),
                        t_sht=round(
                            (get_float_value_with_dot(
                                operation, 'VGW02'
                            )) / get_float_value_with_dot(
                                operation, 'BMSCH'
                            ) * 60 * 10000) / 10000,
                        t_pz=0,
                        t_nal=get_float_value_with_dot(
                            operation, 'VGW01'
                        ) * 60
                    )
                    continue

                if get_float_value_with_dot(operation, 'VGW02') > get_float_value_with_dot(operation, 'VGW03'):
                    percent = get_float_value_with_dot(
                            operation, 'VGW06'
                        )
                    parent.add_operation(
                        version_id=version_id,
                        operation_id='{}_{}_{}с'.format(
                            get_text_value(material, 'MATNR'),
                            version_id,
                            get_text_value(operation, 'VORNR')
                        ),
                        equipment=get_text_value(operation, 'ARBID'),
                        department=dept,
                        nop=get_text_value(operation, 'VORNR'),
                        name=get_text_value(operation, 'LTXA1'),
                        t_sht=round(
                            (get_float_value_with_dot(
                                operation, 'VGW02'
                            ) - get_float_value_with_dot(
                                operation, 'VGW03'
                            )) / get_float_value_with_dot(
                                operation, 'BMSCH'
                            ) * percent / 100 * 60 * 10000) / 10000,
                        t_pz=0,
                        t_nal=0
                    )
                    parent.add_operation(
                        version_id=version_id,
                        operation_id='{}_{}_{}р'.format(
                            get_text_value(material, 'MATNR'),
                            version_id,
                            get_text_value(operation, 'VORNR')
                        ),
                        equipment=get_text_value(operation, 'ARBID'),
                        department=dept,
                        nop=get_text_value(operation, 'VORNR'),
                        name=get_text_value(operation, 'LTXA1'),
                        t_sht=round(
                            get_float_value_with_dot(
                                operation, 'VGW03'
                            ) / get_float_value_with_dot(
                                operation, 'BMSCH'
                            ) * get_float_value_with_dot(
                                operation, 'VGW06'
                            ) / 100 * 60 * 10000) / 10000,
                        t_pz=0,
                        t_nal=0
                    )
                else:
                    parent.add_operation(
                        version_id=version_id,
                        operation_id='{}_{}_{}р'.format(
                            get_text_value(material, 'MATNR'),
                            version_id,
                            get_text_value(operation, 'VORNR')
                        ),
                        equipment=get_text_value(operation, 'ARBID'),
                        department=dept,
                        nop=get_text_value(operation, 'VORNR'),
                        name=get_text_value(operation, 'LTXA1'),
                        t_sht=round(max(
                            get_float_value_with_dot(operation, 'VGW02'),
                            get_float_value_with_dot(operation, 'VGW03')
                        ) / get_float_value_with_dot(
                            operation, 'BMSCH'
                        ) * get_float_value_with_dot(
                            operation, 'VGW06'
                        ) / 100 * 60 * 10000) / 10000,
                        t_pz=0,
                        t_nal=0
                    )
        return report
