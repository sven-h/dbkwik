import logging
import csv
import re
import os
from os import path
import gzip
import ujson
from itertools import combinations

def get_titles_from_dump_fast(file_handle):
    #title_finder = re.compile(r"<title>(.*?)</title>[ \n]*?<ns>0</ns>")
    title = set()
    title_finder = re.compile(r"<title>(.*?)</title>")
    #with open('509_en_harrypotter_pages_current.xml', 'r', encoding='utf8') as f:
    for line in file_handle: # f:
        m = title_finder.search(line)
        if m is not None:
            #print(m.group(1))
            if "<ns>0</ns>" in next(file_handle):
                title.add(m.group(1))
    return title

def remove_common_pages(wiki_title_set):
    wiki_title_set.discard('Main Page')
    wiki_title_set.discard('Sandbox')
    wiki_title_set.discard('Hauptseite')
    return wiki_title_set

def select_gold_wikis(wiki_metadata_file, dump_folder):

    if path.isfile('./possible_gold_standard_wikis_cache.json'):
        with open('./possible_gold_standard_wikis_cache.json', 'r') as f:
            wiki_list = ujson.load(f)
    else:
        wiki_list = []
        # dict wiki_id -> dump path
        wiki_ids_with_dump = dict([(int(file_name.split('~')[0]), path.join(dump_folder, file_name)) for file_name in os.listdir(dump_folder) if path.isfile(path.join(dump_folder, file_name))])
        with open(wiki_metadata_file, newline='', encoding='utf8') as f:
            reader = csv.reader(f)
            next(reader)
            i = 0
            for row in reader:
                # only wikis in english and a downloadable dump and article amount greater than 100
                if row[9] == "en" and int(row[0]) in wiki_ids_with_dump and int(row[16]) > 100:
                    wiki_dump_path = wiki_ids_with_dump[int(row[0])]
                    with gzip.open(wiki_dump_path, 'rt', encoding='utf8') as f:
                        wiki_titles = remove_common_pages(get_titles_from_dump_fast(f))
                        wiki_list.append((row, wiki_titles))
        with open('./possible_gold_standard_wikis_cache.json', 'w') as f:
            ujson.dump(wiki_list, f)


    with open('possible_gold_standard_wikis.csv', 'w', encoding='utf8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Source ID', 'Source title', 'Source domain', 'Source hub', 'Source topic', 'Target ID', 'Target title', 'Target domain','Target hub', 'Target topic', '#Overlapping Titles', 'Jaccard'])
        for (src_row, src_titles), (dst_row, dst_titles) in combinations(wiki_list, 2):
            wiki_intersection = set(src_titles).intersection(set(dst_titles))
            if len(wiki_intersection) > 3:
                wiki_union = set(src_titles).union(set(dst_titles))
                writer.writerow(
                    [src_row[0], src_row[1], src_row[7],src_row[8], src_row[10],
                     dst_row[0], dst_row[1], dst_row[7],dst_row[8], dst_row[10],
                     len(wiki_intersection),
                     "{:.6f}".format(len(wiki_intersection) / len(wiki_union))])



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    select_gold_wikis('wikis.csv', 'dump')
