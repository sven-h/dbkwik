from __future__ import division
import logging
import glob
from AlignmentFormat import parse_mapping_from_file, get_confusion_matrix
import ujson
import bz2
from nparser import parse
import os
from collections import defaultdict
import tarfile
import io
from rdflib import Graph, RDFS, RDF, OWL
from gensim.models.doc2vec import Doc2Vec
from scipy import spatial
import operator

from util_interwiki_match_func import my_match_classes, my_match_properties, my_match_instance_direct, my_match_instance_doc2vec
from util_eval import get_mapping_with_type, compute_micro_macro, get_results, find_threshold_by_cross_val, filter_mapping_domain, __filter_mapping_threshold

class all_match:
    def __init__(self):
        self.lowercased = defaultdict(lambda: defaultdict(list))

    def add_one_wiki(self, label_resource_list, domain):
        #get domain
        #check if we have multiple labels
        lowercased_to_resource = defaultdict(list)
        for label, resource in label_resource_list:
            lowercased_to_resource[label.lower()].append((label, resource))
        for label, resources in lowercased_to_resource.items():
            if len(resources) == 1:
                self.lowercased[label]['unique'].append(resources[0][1])
            else:
                self.lowercased[label][domain].extend(resources)


    def get_count_same_cases(self, str_a, str_b):
        count = 0
        for i in range(len(str_a)):
            if (str_a[i].islower() and str_b[i].islower()) or (str_a[i].isupper() and str_b[i].isupper()):
                count += 1
        return count

    def query(self, search, choose_best_one=True, own_domain=''):
        #returns in every case a dict with a unique key and possibly other keys with corresponding (label, resource) list.
        search = search.strip()
        candidates_dict = self.lowercased.get(search.lower(), None)
        if candidates_dict is None:
            return dict()

        ret_dict = dict()
        ret_dict['unique'] = []
        for domain, label_resource_list in candidates_dict.items():
            if domain == 'unique':
                ret_dict['unique'].extend([res for res in label_resource_list if not res.startswith('http://dbkwik.webdatacommons.org/' + own_domain)])
            elif domain == own_domain:
                continue
            else:
                if choose_best_one:
                    list_to_sort = [(self.get_count_same_cases(search, original_label), uri) for (original_label, uri) in label_resource_list]
                    list_to_sort.sort(key=lambda x: x[0], reverse=True)
                    ret_dict['unique'].append(list_to_sort[0][1])
                else:
                    ret_dict[domain] = label_resource_list
        return ret_dict

        # candidates_dict = dict(candidates_dict)
        # candidates_dict.pop(own_domain, None)
        #
        # if choose_best_one:
        #     ret_dict = dict()
        #     ret_dict['unique'] = []
        #     for domain, label_resource_list in candidates_dict.items():
        #         if domain == 'unique':
        #             ret_dict['unique'].extend(label_resource_list)
        #         else:
        #             list_to_sort = [(self.get_count_same_cases(search, original_label), uri) for (original_label, uri) in label_resource_list]
        #             list_to_sort.sort(key=lambda x: x[0], reverse=True)
        #             ret_dict['unique'].append(list_to_sort[0][1])
        #     return ret_dict
        # else:
        #     return candidates_dict



class mapping_indices():
    def __init__(self, doc2vec_path):
        self.classes_index = all_match()
        self.properties_index = all_match()

        self.instance_chooser = 'instances_index'
        self.instances_index = all_match()
        #self.instances_index_with_disambig = all_match()

        self.doc2vec_chooser = 'doc2vec_short_dbow'
        self.doc2vec_short_dbow = Doc2Vec.load(doc2vec_path + 'short-dbow.model')
        #self.doc2vec_long_dbow = Doc2Vec.load(doc2vec_path + 'long-dbow.model')
        #self.doc2vec_short_dm = Doc2Vec.load(doc2vec_path + 'short-dm.model')
        #self.doc2vec_long_dm = Doc2Vec.load(doc2vec_path + 'long-dm.model')


    def process_one_wiki_file(self, wiki_path):
        file_split = os.path.basename(wiki_path).split('~')
        language = file_split[1]
        domain = file_split[2]
        with tarfile.open(wiki_path, 'r', encoding='utf8') as wiki_file:

            redirects = self.wiki_extract_redirects(wiki_file, language)

            self.classes_index.add_one_wiki(self.wiki_extract_classes(wiki_file, language), domain)
            self.properties_index.add_one_wiki(self.wiki_extract_properties(wiki_file, language), domain)
            self.instances_index.add_one_wiki(self.wiki_extract_inst(wiki_file, language, redirects), domain)
            #self.instances_index_with_disambig.add_one_wiki(self.wiki_extract_inst_with_disambig(wiki_file, language, redirects), domain)


    def wiki_extract_redirects(self, wiki_file, language):
        redirects_map = dict()
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-transitive-redirects.ttl".format(language))):
                redirects_map[s.value] = o.value
        except KeyError:
            logging.error("could not find file transitive-redirects.ttl")
        return redirects_map

    def wiki_extract_classes(self, wiki_file, language):
        class_list = []
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-template-type-definitions.ttl".format(language))):
                if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                    class_list.append((o.value, s.value))
        except KeyError:
            logging.error("could not find file template-type-definitions.ttl")
        return class_list

    def wiki_extract_properties(self, wiki_file, language):
        prop_list = []
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-infobox-property-definitions.ttl".format(language))):
                if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                    prop_list.append((o.value, s.value))
        except KeyError:
            logging.error("could not find file infobox-property-definitions.ttl")
        return prop_list

    def wiki_extract_inst(self, wiki_file, language, redirects):
        inst_list = []
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
                if redirects.get(s.value, None) is not None:
                    continue  # do not use redirects labels
                inst_list.append((o.value.strip(), s.value))
        except KeyError:
            logging.error("could not find file labels.ttl")
        return inst_list

    def wiki_extract_inst_with_disambig(self, wiki_file, language, redirects):
        disambig = defaultdict(set)
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-disambiguations.ttl".format(language))):
                disambig[s.value].add(o.value)
        except KeyError:
            logging.error("could not find file disambiguations.ttl")

        inst_list = []
        try:
            for s, p, o in parse(wiki_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
                if redirects.get(s.value, None) is not None:
                    continue  # do not use redirects labels
                inst_list.append((o.value.strip(), s.value))
                for r in disambig.get(s.value, set()):
                    inst_list.append((o.value.strip(), r))
        except KeyError:
            logging.error("could not find file labels.ttl")
        return inst_list

    def get_class_index(self):
        return self.classes_index

    def get_property_index(self):
        return self.properties_index

    def get_instance_index(self):
        if self.instance_chooser == 'instances_index':
            return self.instances_index
        elif self.instance_chooser == 'instances_index_with_disambig':
            return self.instances_index_with_disambig
        return None

    def get_doc2vec_index(self):
        if self.doc2vec_chooser == 'doc2vec_short_dbow':
            return self.doc2vec_short_dbow
        elif self.doc2vec_chooser == 'doc2vec_long_dbow':
            return self.doc2vec_long_dbow
        elif self.doc2vec_chooser == 'doc2vec_short_dm':
            return self.doc2vec_short_dm
        elif self.doc2vec_chooser == 'doc2vec_long_dm':
            return self.doc2vec_long_dm
        return None



def get_index_wiki_redirects(wiki_tar_file, language):
    redirects_map = dict()
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-transitive-redirects.ttl".format(language))):
            redirects_map[s.value] = o.value
    except KeyError:
        logging.error("could not find file labels.ttl")
    return redirects_map


def run_configurations(match_function, domain_to_dump_file, gold_dir, type, find_threshold, mapping_index, threshold = None):
    all_result = []
    mapping_system_list, gold_list = [], []
    for one_eval in glob.glob(gold_dir):
        wiki_split = os.path.basename(one_eval).split('~')
        source_domain = wiki_split[0]
        target_domain = wiki_split[1]

        wiki_file = domain_to_dump_file.get(source_domain, None)
        if wiki_file is None:
            continue

        logging.info("{} <-> {}".format(source_domain, target_domain))
        mapping_gold, onto1, onto2, extension = parse_mapping_from_file(one_eval)
        gold_class, gold_property, gold_instance = get_mapping_with_type(mapping_gold)

        # mapping system
        language = os.path.basename(wiki_file).split('~')[1]
        domain = os.path.basename(wiki_file).split('~')[2]
        with tarfile.open(wiki_file, 'r', encoding='utf8') as in_tar:
            #logging.info("read redirects")
            wiki_redirect_index = get_index_wiki_redirects(in_tar, language)
            #logging.info("match")
            system_results = match_function(in_tar, language, mapping_index, domain, wiki_redirect_index)
            #logging.info("match finish")

        system_results = filter_mapping_domain(system_results, 'http://dbkwik.webdatacommons.org/' + target_domain)
        if threshold is not None:
            system_results = __filter_mapping_threshold(system_results, threshold)

        mapping_system_list.append(system_results)
        if type == 'class':
            all_result.append(get_results(system_results, gold_class, True, True))
            gold_list.append(gold_class)
        elif type == 'prop':
            all_result.append(get_results(system_results, gold_property, True, True))
            gold_list.append(gold_property)
        elif type == 'inst':
            all_result.append(get_results(system_results, gold_instance, True, True))
            gold_list.append(gold_instance)

    if find_threshold:
        find_threshold_by_cross_val(mapping_system_list, gold_list)
    else:
        micro_macro = compute_micro_macro(all_result)
        logging.info(
            "macro: prec: {} recall: {}  f-measure: {}".format(micro_macro[0][0], micro_macro[0][1], micro_macro[0][2]))
        logging.info(
            "micro: prec: {} recall: {}  f-measure: {}".format(micro_macro[1][0], micro_macro[1][1], micro_macro[1][2]))


def evaluate_interwiki_mapping():
    gold_dir, dump_dir, doc2vec_path = 'gold/interwiki/*.xml', 'all_files/*.tar.gz', 'model/'

    my_mapping_index = mapping_indices(doc2vec_path)
    for wiki_file in glob.glob(dump_dir):
        if os.path.basename(wiki_file).split('~')[0] in ['304', '691244', '1267847', '2233', '330278', '2237', '113', '745', '323']: #['304', '691244']: #['304', '691244', '1267847', '2233', '330278', '2237', '113', '745', '323']:
            my_mapping_index.process_one_wiki_file(wiki_file)

    domain_to_dump_file = {os.path.basename(wiki_file).split('~')[2]: wiki_file for wiki_file in glob.glob(dump_dir)}

    # run_configurations(my_match_classes, domain_to_dump_file, gold_dir, 'class', False, my_mapping_index)
    # run_configurations(my_match_properties, domain_to_dump_file, gold_dir, 'prop', False, my_mapping_index)

    my_mapping_index.instance_chooser = 'instances_index'

    logging.info("instances_index")

    logging.info("doc2vec_short_dbow")
    my_mapping_index.doc2vec_chooser = 'doc2vec_short_dbow'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.416)

    logging.info("doc2vec_long_dbow")
    my_mapping_index.doc2vec_chooser = 'doc2vec_long_dbow'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.5)

    logging.info("doc2vec_short_dm")
    my_mapping_index.doc2vec_chooser = 'doc2vec_short_dm'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.143)

    logging.info("doc2vec_long_dm")
    my_mapping_index.doc2vec_chooser = 'doc2vec_long_dm'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.203)



    logging.info("instances_index_with_disambig")
    my_mapping_index.instance_chooser = 'instances_index_with_disambig'

    logging.info("doc2vec_short_dbow")
    my_mapping_index.doc2vec_chooser = 'doc2vec_short_dbow'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.416)

    logging.info("doc2vec_long_dbow")
    my_mapping_index.doc2vec_chooser = 'doc2vec_long_dbow'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.5)

    logging.info("doc2vec_short_dm")
    my_mapping_index.doc2vec_chooser = 'doc2vec_short_dm'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.143)

    logging.info("doc2vec_long_dm")
    my_mapping_index.doc2vec_chooser = 'doc2vec_long_dm'
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, my_mapping_index)
    run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', False, my_mapping_index, 0.203)





####apply

def apply_model_to_one(wiki_file,output_file, mapping_index):
    language = os.path.basename(wiki_file).split('~')[1]
    domain = os.path.basename(wiki_file).split('~')[2]
    with tarfile.open(wiki_file, 'r', encoding='utf8') as in_tar:
        with open(output_file + os.path.basename(wiki_file), 'w') as out_file:
            wiki_redirect_index = get_index_wiki_redirects(in_tar, language)
            for source, target, relation, confidence in my_match_classes(in_tar, language, mapping_index, domain, wiki_redirect_index):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}>.\n".format(source, target))
            for source, target, relation, confidence in my_match_properties(in_tar, language, mapping_index, domain, wiki_redirect_index):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}>.\n".format(source, target))
            for source, target, relation, confidence in __filter_mapping_threshold(my_match_instance_doc2vec(in_tar, language, mapping_index, domain, wiki_redirect_index), 0.416):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#sameAs> <{}>.\n".format(source, target))


def apply_model():
    #import multiprocessing
    #from functools import partial

    dump_dir, doc2vec_path = 'all_files/*.tar.gz', 'model/'

    my_mapping_index = mapping_indices(doc2vec_path)
    my_mapping_index.doc2vec_chooser = 'doc2vec_short_dbow'
    for i, wiki_file in enumerate(glob.glob(dump_dir)):
        my_mapping_index.process_one_wiki_file(wiki_file)

    for wiki_file in glob.glob(dump_dir):
        apply_model_to_one(wiki_file, 'internal_mapping_doc2vec/', my_mapping_index)



def main():
  
    #evaluate_interwiki_mapping()
    apply_model()



if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='b_evaluate_interwiki.log',filemode='w', level=logging.INFO)
    main()
