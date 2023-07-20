import csv
from argparse import ArgumentParser
from datetime import datetime
from os import getcwd
from os.path import join
from xml.etree.ElementTree import parse

import yaml
from tqdm import tqdm

from logic.read_from_folder import ReadSession
from logic.xml_tools import get_text_value, get_float_value_with_dot
from tools.ia_rest import IAImportExport

ASM_DEPTS = ['1011', '1015', '1012', '1013', '7403',
             '1014', '1019', '1017', '0716', 'N101', '1104']
WIP_DEPT_TO_SKIP = []
DEPT_TO_SKIP = []


def read_from_file(xml_file):
    tree = parse(xml_file)
    root = tree.getroot()
    report = {}

    # читаем все фреймы в исходном файле
    rows = root.findall('MAT_DATA')

    for material in tqdm(rows, desc='Считываем XML'):
        # читаем идентификатор ДСЕ
        product = get_text_value(material, "MATNR")
        # читаем все строки НЗП по этой ДСЕ
        wip_rows = material.findall('MT_STOCK')
        # читаем все заказы плана по этой ДСЕ
        for stock_row in wip_rows:
            skip = False
            # игнорирую НЗП в некоторых подразделениях
            for dept in WIP_DEPT_TO_SKIP:
                if dept in str(get_text_value(stock_row, 'LGORT')):
                    skip = True
                    break
            if skip:
                continue
            # придумаем как назвать идентификатор партии
            # условие -- ID должно быть уникальным.
            # В нашем случае ДСЕ-Подразделение где лежит НЗП обещает
            # быть уникально в виду логики формирования этого НЗП
            stock = get_text_value(stock_row, 'LGORT')
            if stock not in report:
                report[stock] = {}
            if product not in report[stock]:
                report[stock][product] = 0
            # В LABST лежит количество
            amount = get_float_value_with_dot(stock_row, 'LABST')
            report[stock][product] += amount

    return report


def main():
    from logic import read_from_ftp

    parser = ArgumentParser(
        description='Инструмент консольной генерации отчетов '
                    'по результатам моделирования.'
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'kk_wip_parser.yml'))
    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))
    args = parser.parse_args()

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)

    sftpURL = server['sftpURL']
    sftpUser = server['sftpUser']
    sftpPass = server['sftpPass']

    with IAImportExport.from_config(config['instance']) as session:
        report = []
        special_items = []
        all_items = set()
        # for row in session.get_from_rest_collection('entity'):
        #     if row['entity_type_id'] is None:
        #         continue
        #     all_items.add(row['identity'])
        #     if '-' in row['identity'] and '(' not in row['identity']:
        #         report.append({
        #             'OP_ID': row['identity'],
        #             'CODE': row['identity']
        #         })
        #         special_items.append(row['identity'])
        # dict2csv(report, 'special_items.csv')

    sftpPath = config['path']

    session = ReadSession()
    session.read_from_folder(
        config['input']['backup'],
        '_'
    )
    # test_spec = session.entities['107600901394-A0131'].get_back_spec()
    # for child in test_spec:
    #     print(child.code, child.product.name, test_spec[child])
    xml_data = read_from_ftp.read_plan_from_ftp(
        sftpURL, sftpUser, sftpPass, sftpPath
    )

    wip = []
    products = []
    plan = []

    for stock in tqdm(xml_data, desc='Разбор данных'):
        for entity in xml_data[stock]:
            # Возможны два варианта MATNR у ДСЕ:
            # 1. 18 символов (преимущественно цифр) с 6 нулями впереди --
            # это прямо ДСЕ
            # 2. 12 символов, дефис, 5 символов -- это полуфабрикаты той ДСЕ,
            # которая в первых 12 символах
            #
            # текстовой логикой снизу я из кода полуфабриката получаю код ДСЕ
            skip = True
            # if '-' in entity and stock in ASM_DEPTS:
            if entity not in session.entities:
                tqdm.write(f"Не знаю номенклатуру с кодом {entity}")
            else:
                for name in config['products']:
                    if session.entities[entity].product is None:
                        continue
                    if session.entities[entity].product.name is None:
                        continue
                    if name in session.entities[entity].product.name.lower():
                        skip = False
                        break
                if not skip:
                    spec_report = session.entities[entity].get_back_spec()
                    for child, amount in spec_report.items():
                        if amount == 0:
                            continue
                        if child.product is None:
                            tqdm.write(f"Не определилось изделие для ДСЕ {child.code}, а оно входит в {entity}")
                            continue
                        if amount > 0:
                            plan.append({
                                'ORDER': f"{stock}_{entity}_"
                                         f"{session.entities[entity].product.name}_"
                                         f"{round(xml_data[stock][entity])}",
                                'CODE': child.code,
                                'NAME': child.product.name,
                                'AMOUNT': amount * round(xml_data[stock][entity]),
                                'DATE_FROM': datetime.now().strftime('%Y-%m-%d'),
                                'DATE_TO': datetime.now().strftime('%Y-%m-%d')
                            })
                        if amount < 0:
                            wip.append({
                                'BATCH_ID': f"{stock}_{entity}_"
                                         f"{session.entities[entity].product.name}_"
                                         f"{round(xml_data[stock][entity])}_"
                                         f"{child.code}",
                                'ORDER': f"{stock}_{entity}_"
                                         f"{session.entities[entity].product.name}_"
                                         f"{round(xml_data[stock][entity])}",
                                'CODE': child.code,
                                'AMOUNT': abs(amount) * round(xml_data[stock][entity]),
                                'INIT_AMOUNT': '',
                                'OPERATION_ID': '',
                                'OPERATION_PROGRESS': 100,
                            })
                    for row in session.entities[entity].back_spec:
                        products.append({
                            'ГДЕ ЛЕЖИТ': stock,
                            'ЧТО ЛЕЖИТ КОД': entity,
                            'ЧТО ЛЕЖИТ НАЗВАНИЕ': session.entities[entity].product.name,
                            'ЧТО ЛЕЖИТ КОЛИЧЕСТВО': round(
                                xml_data[stock][entity] * 1000
                            ) / 1000,
                            'КУДА ВХОДИТ КОД': row.code,
                            'КУДА ВХОДИТ НАЗВАНИЕ': row.product.name,
                            'КУДА ВХОДИТ КОЛИЧЕСТВО': session.entities[entity].back_spec[row]
                        })
                    continue

            if '-' in entity:
                product = entity[:12].zfill(18)
            else:
                product = entity

            for item in special_items:
                if item in entity:
                    product = entity[:18]
                    break

            # if product not in all_items:
            #     continue

            if entity[:18] != product:
                wip.append({
                    'BATCH_ID': f"{entity}_{stock}",
                    'CODE': product,
                    'INIT_AMOUNT': xml_data[stock][entity],
                    'AMOUNT': round(
                        xml_data[stock][entity] * 1000
                    ) / 1000,
                    'OPERATION_ID': entity,
                    'OPERATION_PROGRESS': 0,
                    'ORDER': ''
                })
            else:
                wip.append({
                    'BATCH_ID': f"{entity}_{stock}",
                    'CODE': product,
                    'INIT_AMOUNT': xml_data[stock][entity],
                    'AMOUNT': round(
                        xml_data[stock][entity] * 1000
                    ) / 1000,
                    'OPERATION_ID': '',
                    'OPERATION_PROGRESS': 100,
                    'ORDER': ''
                })

    keys = products[0].keys()
    with open('products.csv', 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(products)
    keys = plan[0].keys()
    with open('plan.csv', 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(plan)
    keys = wip[0].keys()
    with open(config['output']['wip'], 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(wip)


if __name__ == '__main__':
    main()
