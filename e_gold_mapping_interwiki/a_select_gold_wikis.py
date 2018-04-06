import csv
import re
import logging
import os
from os import path
import editdistance

def select_gold_wikis(wiki_metadata_file, dump_folder):
    wiki_ids_with_dump = set([int(file_name.split('~')[0]) for file_name in os.listdir(dump_folder) if path.isfile(path.join(dump_folder, file_name))])


    similar_wikis = {} # map from a canonical representative to a set of all similar wikis (levenstein <= 1)
    with open(wiki_metadata_file, newline='', encoding='utf8') as f:
        reader = csv.reader(f)
        next(reader)
        i = 0
        for row in reader:
            # only wikis in english and a downloadable dump and article amount greater than 100
            if row[9] == "en" and int(row[0]) in wiki_ids_with_dump and int(row[16]) > 100:
                domain = row[2][7:row[2].index('.wikia.com')] #remove http://

                found = False
                for key, value in similar_wikis.items():
                    if editdistance.eval(domain, key) <= 1:
                        value.add(domain)
                        found = True
                if not found:
                    similar_wikis[domain] = set([domain])

                #print(row)
                #print(domain)
                #i += 1

    for key, value in similar_wikis.items():
        if len(value) > 1:
            print(value)
    print(i)


    #print(len(wiki_ids_with_dump))
    #print(wiki_ids_with_dump)



def select_gold_wikis_based_on_title(wiki_metadata_file):
    test = []
    regex_wiki = re.compile(r"wiki[a]?")
    regex_only_alphanum = re.compile(r"[^a-z0-9 ]+")
    with open(wiki_metadata_file, newline='', encoding='utf8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            #only wikis in english with a downloadlink
            if row[9] == "en" and row[24] != "":
                #print(row[1])
                title = row[1]
                #mod_title = title.lower().replace('wikia ', '').replace(' wikia', '').replace(' wiki', '').replace('wiki ', '').replace('-', ' ').replace('!', '').strip()
                mod_title = regex_wiki.sub('', regex_only_alphanum.sub('', title.lower())).replace('  ', ' ').strip()
                #print("\"{}\" -> \"{}\"".format(title, mod_title))
                #print(mod_title)
                test.append(mod_title)
    #print(len(test))
    return test






def compute_str_dist_one_cluster(wiki_titles):
    import pylev



def compute_cluster(wikis):
    #from leven import levenshtein
    import pylev
    from sklearn.cluster import dbscan
    from sklearn.metrics.pairwise import pairwise_distances
    import numpy as np
    from functools import partial

    strings = wikis[:1000]#['cityblock', 'cosine', 'euclidean', 'l1', 'l2', 'manhattan']
    print(strings)

    def lev_metric(x, y):
        i, j = int(x[0]), int(y[0])
        #return levenshtein(strings[i], strings[j])
        return pylev.levenshtein(strings[i], strings[j])

    def mylev(s, u, v):
        return pylev.levenshtein(s[int(u)], s[int(v)])

    print(dbscan(np.arange(len(strings)).reshape(-1, 1), metric=lev_metric))

    #print(pairwise_distances(np.arange(len(strings)).reshape(-1, 1), metric=partial(mylev, strings)))

def compute_cluster_2(wikis):
    #from collections import defaultdict
    from collections import Counter

    #test = defaultdict(list)
    #for wiki in wikis:
    #    test[wiki].append(wiki)
    print(Counter(wikis).most_common())



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='b_select_gold_wikis_based_on_content.log', filemode='w',
                        level=logging.INFO)
    select_gold_wikis('../a_download_wikia/2018_02_27_wikis.csv', 'D:/dbkwik/2018_02_27_dbkwik/a_dump')
    #get_wikis()
    #compute_cluster(get_wikis('../wiki_metadata.csv'))