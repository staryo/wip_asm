import csv
from os import path


def dict2csv(dictlist, csvfile, chunksize=5000000):
    """
    Takes a list of dictionaries as input and outputs a CSV file.
    """
    keys = dictlist[0].keys()
    num = 0
    if len(dictlist) < chunksize:
        with open(csvfile, 'w', newline='', encoding="utf-8") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(dictlist)
    else:
        name, extension = path.splitext(csvfile)
        while num*chunksize < len(dictlist):
            num += 1
            with open('{}_{}.{}'.format(name, num, extension), 'w', newline='',
                      encoding="utf-8") as output_file:
                dict_writer = csv.DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(
                    dictlist[(num-1)*chunksize: num*chunksize])
