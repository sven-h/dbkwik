import logging
import gzip
import glob
import re
from collections import defaultdict
import hashlib
import filecmp
import ujson
import csv
import os
import requests
import random

def get_titles_from_dump_fast(file_handle):
    #title_finder = re.compile(r"<title>(.*?)</title>[ \n]*?<ns>0</ns>")
    title = []
    title_finder = re.compile(r"<title>(.*?)</title>")
    #with open('C:\\dev\\dbkwik_extraction\\dbkwik_own\\dumps\\transformed\\509_en_harrypotter_pages_current.xml', 'r', encoding='utf8') as f:
    for line in file_handle: # f:
        m = title_finder.search(line)
        if m is not None:
            #print(m.group(1))
            if "<ns>0</ns>" in next(file_handle):
                title.append(m.group(1))
    return title

def check_sitename():
    sitename_finder = re.compile(r"<sitename>(.*?)</sitename>")
    for dump_path in glob.glob('D:\\dbkwik\\unzipped\\dump\\*'):
        #logging.info(dump_path)
        with gzip.open(dump_path, 'rt') as dump_file:
            for line in dump_file:
                m = sitename_finder.search(line)
                if m is not None:
                    logging.info(m.group(1))
                    logging.info(dump_path)
                    logging.info('--------')
                    break

def write_same_wikis():
    logging.info("Compute similar files")
    similar_files = defaultdict(list)
    for i, dump_path in enumerate(glob.glob('D:\\dbkwik\\unzipped\\dump\\*')):
        with gzip.open(dump_path, 'r') as dump_file:
            similar_files[dump_file.read(500)].append(dump_path)
        if i % 1000 == 0:
            logging.info(i)
        #if i > 1000:
        #    break

    possible_dup = set()
    for first_chars, dump_paths in similar_files.items():
        if len(dump_paths) > 1:
            #print('Same: ' + str(dump_paths))
            possible_dup.update(dump_paths)

    logging.info("Compute hash for %s files", len(possible_dup))
    #second run
    same_files = defaultdict(list)
    for i, dump_path in enumerate(possible_dup):
        with gzip.open(dump_path, 'rb') as dump_file:
            h = hashlib.md5()#.sha256()
            for b in iter(lambda: dump_file.read(128 * 1024), b''):
                h.update(b)
                same_files[h.hexdigest()].append(dump_path)
        if i % 100 == 0:
            logging.info(i)

    with open('same_wikis.jsonl', 'w') as out_file:
        for md5, dump_paths in similar_files.items():
            if len(dump_paths) > 1:
                out_file.write(ujson.dumps(dump_paths) + "\n")
                #print('Same: ' + str(dump_paths))


def decide_for_correct_dump():
    wikis = defaultdict(dict)
    with open('wikis.csv', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        next(csvreader)
        for row in csvreader:
            wikis[int(row[0])] = {
                'stats_articles' : int(row[16]),
                'stats_pages' : (row[17])
            }

    with open('same_wikis.jsonl', 'r') as in_file:
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        next(in_file)
        for line in in_file:
            same_dumps = ujson.loads(line)
            print(same_dumps)

            with gzip.open(same_dumps[0], 'rt', encoding='utf-8') as dump_file:
                titles = get_titles_from_dump_fast(dump_file)

            dump_dict = { k : 0 for k in same_dumps}

            #test = random.sample(titles, 10)

            random.shuffle(titles)
            for one_title in titles[:10]:
                #print("test")

            #while len(dump_dict) > 1:
                #one_title = random.choice(titles)
                for my_dump in dump_dict.keys():
                    url = 'http://' + os.path.basename(my_dump).split('~')[2] + '.wikia.com/wiki/' + one_title.replace(' ', '_')
                    #print(url)
                    if requests.head(url).status_code == 200:
                        dump_dict[my_dump] += 1

                maxValue = max(dump_dict.values())
                #if maxValue > 10:
                #    break
                dump_dict = {key : dump_dict[key] for key in dump_dict.keys() if dump_dict[key]==maxValue}
                if len(dump_dict) <= 1:
                    break

            print(dump_dict)

            # dump_set = set(same_dumps)
            # while len(dump_set) > 1:
            #     one_title = random.choice(titles)
            #     for my_dump in list(dump_set):
            #         url = 'http://' + os.path.basename(my_dump).split('~')[2] + '.wikia.com/wiki/' + one_title.replace(' ', '_')
            #         if requests.head(url).status_code != 200:
            #             dump_set.remove(my_dump)
            #
            # print(dump_set)

            #with gzip.open(same_dumps[0], 'rt', encoding='utf-8') as dump_file:
            #    actual_dump_pages = len(get_titles_from_dump_fast(dump_file))
            #print(actual_dump_pages)
            #for dump_file in same_dumps:
            #    wiki_id = int(os.path.basename(dump_file).split('~')[0])
            #    print("wiki_id: {}, articles: {} pages: {}".format(wiki_id, wikis[wiki_id]['stats_articles'], wikis[wiki_id]['stats_pages']))
            #print("--------")



def retrive_wrong_dump_url():
    wiki_has_link = {}
    with open('new_crawl.csv', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            wiki_has_link[int(row[1])] = (row[5] != "")
    print(wiki_has_link[1345919])

    with open('same_wikis.jsonl', 'r') as in_file:
        for line in in_file:
            same_dumps = ujson.loads(line)
            #counter = 0
            same = []
            for path in same_dumps:
                if wiki_has_link[int(os.path.basename(path).split('~')[0])]:
                    same.append(os.path.basename(path).split('~')[3][:-3])#counter += 1
            if len(same) > 1:
                print(','.join(same))

def changed_url():
    with open('new_crawl.csv', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            if row[4] != row[5] and row[5] != '':
                print(row)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    #write_same_wikis()
    #decide_for_correct_dump()
    changed_url()
