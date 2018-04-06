from __future__ import division
import logging
from nparser import parse
from collections import defaultdict


def get_mappings_count_and_unique(dump_path, name):
    subjects = set()
    count = 0
    with open(dump_path + name, 'rb') as f:
        for s, p, o in parse(f):
            subjects.add(s.value)
            count += 1
    return len(subjects), count


def analysis_after(dump_path):

    subj_doc2vec, count_doc2vec = get_mappings_count_and_unique(dump_path, 'dbpedia_mapping_doc2vec.txt')
    subj_string, count_string = get_mappings_count_and_unique(dump_path, 'dbpedia_mapping_string.txt')

    print("doc2vec:")
    print("subjects: {}".format(subj_doc2vec))
    print("count: {}".format(count_doc2vec))
    print("string:")
    print("subjects: {}".format(subj_string))
    print("count: {}".format(count_string))

if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_mapping.log', filemode='w',level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    analysis_after('sorted')
