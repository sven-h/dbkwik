import logging
import glob
from os import path
from AlignmentFormat import serialize_mapping_to_file
import ujson
import os
import tarfile
from nparser import parse

def get_id_and_url(mapping):
    one_url = mapping[0][0]
    start_str = 'dbkwik.webdatacommons.org/'
    start_index = one_url.index(start_str)+len(start_str)
    end_index = one_url.index('/', start_index)
    return one_url[start_index:end_index], one_url[:end_index]

def add_subjects(subjects, tar_file, name):
    try:
        for s, p, o in parse(tar_file.extractfile(name)):
            subjects.add(s.value)
    except KeyError:
        logging.error("could not find file {}".format(name))


def get_redirects_map_and_subjects(file_path, domain_to_dump_file):
    wiki_domain = os.path.basename(file_path).split('~')[0]
    redirects_map = dict()
    subjects = set()
    dump_file = domain_to_dump_file[wiki_domain]
    language = os.path.basename(dump_file).split('~')[1]
    with tarfile.open(dump_file, 'r', encoding='utf8') as wiki_tar_file:
        try:
            for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-transitive-redirects.ttl".format(language))):
                redirects_map[s.value] = o.value
        except KeyError:
            logging.error("could not find file transitive.ttl")

        add_subjects(subjects, wiki_tar_file, "{}wiki-20170801-labels.ttl".format(language))
        add_subjects(subjects, wiki_tar_file, "{}wiki-20170801-short-abstracts.ttl".format(language))
        add_subjects(subjects, wiki_tar_file, "{}wiki-20170801-infobox-property-definitions.ttl".format(language))
        add_subjects(subjects, wiki_tar_file, "{}wiki-20170801-template-type-definitions.ttl".format(language))
    return redirects_map, subjects


def refine_gold_standard():
    domain_to_dump_file = {os.path.basename(wiki_file).split('~')[2]: wiki_file for wiki_file in glob.glob('../g_evaluate_mappings/dumps/*.tar.gz')}
    for file in glob.glob('./original/*'):
        redirects_map, subject_set = get_redirects_map_and_subjects(file, domain_to_dump_file)
        with open(file, 'rb') as f:
            print(file)
            for s, p, o in parse(f):
                new_subject = redirects_map.get(s.value, s.value)
                if new_subject != s.value:
                    print("Redirect: {} -> {}".format(s.value, new_subject))

                if new_subject not in subject_set:
                    print("Resource not found: {}".format(new_subject))



def with_null_mapping():
    domain_to_dump_file = {os.path.basename(wiki_file).split('~')[2]: wiki_file for wiki_file in glob.glob('../g_evaluate_mappings/dumps/*.tar.gz')}
    for file in glob.glob('./original/*'):
        alignments = []
        with open(file, 'rb') as f:
            print(file)
            for s,p,o in parse(f):
                if o.value == "null":
                    alignments.append((s.value, 'null', '%', 1.0))
                else:
                    alignments.append((s.value, o.value, '=', 1.0))
        serialize_mapping_to_file('./gold/' + path.basename(file),
                                  sorted(alignments, key=lambda x: x[0]),
                                  get_id_and_url(alignments),
                                  ('dbpedia', 'http://dbpedia.org'))


def main():
    for file in glob.glob('./original/*'):
        alignments = []
        no_matches = []
        with open(file, 'r', newline='', encoding='utf-8') as f:
            for l in f:
                if l.strip().startswith('#'):
                    continue
                first = l[l.index('<') + 1:l.index('>')].replace('/ontology/', '/class/')
                last = l[l.rindex('<') + 1:l.rindex('>')]

                if last == 'null':
                    no_matches.append(first)
                    continue
                #print("{} ---> {}".format(first, last))
                alignments.append((first,last, '=',1.0))

            serialize_mapping_to_file('./gold/' + path.basename(file),
                                      sorted(alignments, key=lambda x: x[0]),
                                      get_id_and_url(alignments),
                                      ('dbpedia', 'http://dbpedia.org'),
                                      {'onto1_no_matches': ujson.dumps(no_matches), 'onto2_no_matches': ''} )
        #break


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_translate.log',filemode='w', level=logging.INFO)
    with_null_mapping()
    # refine_gold_standard()
