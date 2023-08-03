import os
import sys
from contextlib import closing
from xml.etree.ElementTree import XMLParser, parse, ParseError

import paramiko
from tqdm import tqdm

from logic.xml_tools import get_text_value
from script_plan import read_plan_from_file
from script_wip import read_from_file


def read_plan_from_ftp(url, user, password, path, skip, asm=True):

    client = paramiko.SSHClient()
    # automatically add keys without requiring human intervention
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(url, username=user, password=password)

    with closing(client) as ssh:
        with closing(ssh.open_sftp()) as ftp:
            final_path = path
            check = True
            while check:
                print(
                    sorted(
                        ftp.listdir(
                            path=final_path
                        ), reverse=True
                    )
                )
                check = False
                for i in sorted(
                        ftp.listdir(
                            path=final_path
                        ), reverse=True
                ):
                    # if '2021-02-03' in i or '2021-02-02' in i or '2021-02-01' in i:
                    #     continue
                    lstatout = str(ftp.lstat(
                        '{}/{}'.format(final_path, i)
                    )).split()[0]
                    if 'd' in lstatout:
                        check = True
                        final_path = '{}/{}'.format(final_path, i)
                        break
            tqdm.write('{}/body'.format(final_path))
            with closing(ftp.open('{}/body'.format(final_path))) as f:
                if asm:
                    xml_data = read_from_file(f, skip)
                else:
                    xml_data = read_plan_from_file(f, skip)
    return xml_data


def read_from_ftp(ftp_client, path_to_iter):
    report = []
    for i in sorted(
            ftp_client.listdir(
                path=path_to_iter
            )
    ):
        lstatout = str(ftp_client.lstat(
            '{}/{}'.format(path_to_iter, i)
        )).split()[0]
        if 'd' in lstatout:
            report.append('{}/{}'.format(path_to_iter, i))
    return report


def read_tech_from_ftp(ftp_client, path_to_iter, backup_path, exclude):
    iter1 = tqdm(
        sorted(read_from_ftp(ftp_client, path_to_iter)),
        desc=path_to_iter,
        file=sys.stdout,
        position=0
    )
    for each_path in iter1:
        if read_from_ftp(ftp_client, each_path):
            read_tech_from_ftp(ftp_client, each_path, backup_path, exclude)
        else:
            backup_file_from_ftp(ftp_client, each_path, backup_path)


def backup_file_from_ftp(ftp_client, path, backup_path):
    try:
        with closing(ftp_client.open('{}/body'.format(path))) as f:
            # парсим xml
            try:
                # ставим utf-8 хардкодом, чтоб
                # никаких неожиданностей не было
                xmlp = XMLParser(encoding="utf-8")
                tree = parse(f, parser=xmlp)
                root = tree.getroot()
            except ParseError:
                tqdm.write('Ошибка чтения файла -- не распознан корень')
                return
            material = root.find('MATERIALDATA')
            if material is None:
                tqdm.write(
                    'Ошибка чтения файла -- не распознан MATERIALDATA')
                return
            version_id = get_text_value(material, 'VERID')
            if version_id is None:
                tqdm.write((
                    'Ошибка чтения файла -- не распознан VERID. Материал {}'
                ).format(
                    get_text_value(material, 'MATNR')
                ))
                version_id = 'FICT'
    except FileNotFoundError:
        tqdm.write(f'Файл не найден {path}/body')

    if get_text_value(material, 'PRIORITY') is None \
            and get_text_value(material, 'STATUS') != 'Z4':
        print(f'\n Ошибочная карточка: {path} -- не указан приоритет')
        print('Материал:', get_text_value(material, 'MATNR'))
    # if '1354C0000012' in get_text_value(material, 'MATNR'):
    #     print(f'\n {path} ')
    #     print(get_text_value(material, 'MATNR'))

    tree.write(os.path.join(backup_path, '{}_{}'.format(
        get_text_value(material, 'MATNR'),
        version_id
    )), encoding='UTF-8')


if __name__ == '__main__':
    sftpURL = 'kk-srv-bfg2.npo.izhmash'
    sftpUser = 'a.a.stolov'
    sftpPass = ';tyfrfnz061083'
    sftpPath = '/home/http_request_collector/app/data/input/data/POST'
    exclude_list = [
        '/home/http_request_collector/app/data/input/data/POST/2020-08-20',
        '/home/http_request_collector/app/data/input/data/POST/2020-08-25',
        '/home/http_request_collector/app/data/input/data/POST/2020-08-26',
        '/home/http_request_collector/app/data/input/data/POST/2020-08-27',

    ]
    backup = '/home/work/Исходные данные/KK/1feb'
    # read_tech_from_ftp(sftpURL, sftpUser, sftpPass,
    #                    sftpPath, backup_path, exclude_list)

    client = paramiko.SSHClient()
    # automatically add keys without requiring human intervention
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(sftpURL, username=sftpUser, password=sftpPass)
    with closing(client) as ssh:
        with closing(ssh.open_sftp()) as ftp:
            path_list = read_from_ftp(ftp, sftpPath)
            for path in path_list:
                if path not in exclude_list:
                    read_tech_from_ftp(ftp, path, backup, exclude_list)
                    exclude_list.append(path)
