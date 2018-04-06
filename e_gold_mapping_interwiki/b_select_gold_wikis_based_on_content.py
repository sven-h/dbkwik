import csv
import re
import logging
from lxml import etree
from time import perf_counter
import glob
import gzip
import ujson
from os import path
from itertools import combinations
from collections import defaultdict

# not used
def get_title_fromdump():
    context = etree.iterparse('509_en_harrypotter_pages_current.xml', events=('end',), tag=('{http://www.mediawiki.org/xml/export-0.6/}title'))
    title = []
    for event, elem in context:
        title.append(elem.text.encode('utf-8'))
    return title


def get_titles_from_dump_fast(file_handle):
    #title_finder = re.compile(r"<title>(.*?)</title>[ \n]*?<ns>0</ns>")
    title = []
    title_finder = re.compile(r"<title>(.*?)</title>")
    #with open('509_en_harrypotter_pages_current.xml', 'r', encoding='utf8') as f:
    for line in file_handle: # f:
        m = title_finder.search(line)
        if m is not None:
            #print(m.group(1))
            if "<ns>0</ns>" in next(file_handle):
                title.append(m.group(1))
    return title

def get_wiki_metadata(wiki_metadata_file):
    wiki_map = {}
    with open(wiki_metadata_file, newline='', encoding='utf8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            wiki_map[row[0]] = {'id':int(row[0]), 'title':row[1], 'hub':row[8], 'topic':row[10], 'lang':row[9], 'articles': int(row[16]), 'domain': row[7]}
    return wiki_map

def create_wiki_file_with_titles():
    wiki_metadata = get_wiki_metadata('../wiki_metadata.csv')
    with open('wiki_titles_new.jsonl', 'w', newline='', encoding='utf8') as json_file:
        i = 1
        for file in glob.glob('D:\\dbkwik\\unzipped\\dump\\*.gz'):
            with gzip.open(file, 'rt', encoding='utf8') as f:
                wiki_id = path.basename(file).split('~')[0]
                wiki_dict = wiki_metadata[wiki_id]
                wiki_dict['titles'] = get_titles_from_dump_fast(f)
                wiki_dict['titles_len'] = len(wiki_dict['titles'])
                json_file.write(ujson.dumps(wiki_dict) + "\n")
                logging.info("Done with %s wikis", i)
                i += 1

def remove_common_pages(wiki_title_set):
    wiki_title_set.discard('Main Page')
    wiki_title_set.discard('Sandbox')
    wiki_title_set.discard('Hauptseite')
    return wiki_title_set

def create_overlapping_figure():
    #[('Main Page', 18161),
    # ('Sandbox', 2389),
    # ('Hauptseite', 1439),
    # ('Current events', 1415),
    # ('Characters', 1413),
    # ('Templates', 1214),
    # ('Portada', 1051),
    # ('Timeline', 743),
    # ('Weapons', 718),
    # ('Human', 704),
    # ('Earth', 701),
    import networkx as nx
    #from networkx.drawing.nx_agraph import write_dot

    wiki_list = []
    i = 1
    G = nx.Graph()
    with open('wiki_titles.jsonl', 'r', encoding='utf8') as json_file:
        for line in json_file:
            wiki = ujson.loads(line)
            wiki['titles'] = remove_common_pages(set(wiki['titles']))
            wiki_list.append(wiki)
            G.add_node(wiki['id'], articles = wiki['articles'], label = wiki['title'])
            logging.info("Done with %s wikis", i)
            i += 1

    logging.info("Finished loading wikis")
    #https://github.com/ekzhu/datasketch

    for src_wiki, dst_wiki in combinations(wiki_list, 2): # [:1000]
        wiki_intersection = set(src_wiki['titles']).intersection(set(dst_wiki['titles']))
        if len(wiki_intersection) > 2:
            G.add_edge(src_wiki['id'], dst_wiki['id'], weight = len(wiki_intersection))
            logging.info(len(wiki_intersection))

    logging.info("Finished computing")
    #write_dot(G, 'file.dot')
    nx.write_graphml(G, "test.graphml")



def create_overlapping_figure_2():
    import networkx as nx
    from collections import Counter
    from operator import itemgetter
    wiki_title_to_id = defaultdict(set)

    logging.info("Start")
    id_to_title = dict()
    #bal = 0
    G = nx.Graph()
    with open('wiki_titles.jsonl', 'r', encoding='utf8') as json_file:
    #with open('wiki_titles_small.jsonl', 'r', encoding='utf8') as json_file:
        for line in json_file:
            wiki = ujson.loads(line)
            wiki_id = wiki['id']
            G.add_node(wiki['id'], articles=wiki['articles'], label=wiki['title'])
            id_to_title[wiki_id] = (wiki['title'], wiki['domain'])
            for title in wiki['titles']:
                wiki_title_to_id[title].add(wiki_id)
            #bal += 1
    #print(len(wiki_title_to_id))
    #print(bal)
    #test = Counter({title: len(wikis) for title, wikis in wiki_title_to_id.items()})
    #print(test.most_common(300))
    logging.info("End reading, start counting")

    edges = defaultdict(int)
    for title, wikis in wiki_title_to_id.items():
        if title == 'Main Page' or title == 'Sandbox' or title == 'Hauptseite' or len(wikis) <= 1:
            continue
        sorted_wiki_list = sorted(list(wikis))
        for src_wiki, dst_wiki in combinations(sorted_wiki_list, 2):
            edges[(src_wiki, dst_wiki)] += 1

    logging.info("End counting, start sorting")

    #sorted_edges = sorted(edges.items(), key=itemgetter(1), reverse=True)
    logging.info("End sorting, start printing")
    more_than_0 = 0
    more_than_1 = 0
    more_than_10 = 0
    more_than_100 = 0
    with open('wikis_to_match.csv', 'w', encoding='utf8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Source title', 'Source domain', 'Target title', 'Target domain', '#Overlapping Titles'])
        for (src_wiki, dst_wiki), count in edges.items():
            #if count >= 1:
            #    more_than_0 += 1
            #if count > 1:
            #    more_than_1 += 1
            #if count > 10:
            #    more_than_10 +=1
            #if count > 100:
            #    more_than_100 += 1


            if count > 100 :
                title_one = id_to_title[src_wiki][1].replace('-', '')
                title_two = id_to_title[dst_wiki][1].replace('-', '')
                if title_one != title_two:
                #G.add_edge(src_wiki, dst_wiki, weight=count)
                    writer.writerow([id_to_title[src_wiki][0], id_to_title[src_wiki][1], id_to_title[dst_wiki][0], id_to_title[dst_wiki][1], count])
            #print("{} ({}) ---{}---> {} ({})".format(id_to_title[src_wiki][0], id_to_title[src_wiki][1], count, id_to_title[dst_wiki][0], id_to_title[dst_wiki][1]))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='b_select_gold_wikis_based_on_content.log', filemode='w', # filemode='a'
                        level=logging.INFO)

    create_overlapping_figure_2()
    #create_overlapping_figure()
    #create_wiki_file_with_titles()
    #get_wikis()
    #start = perf_counter()
    ##print(regex_test())
    #print(perf_counter() - start)