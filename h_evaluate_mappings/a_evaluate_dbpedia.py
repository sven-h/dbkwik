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

from util_dbpedia_match_func import my_match_classes, my_match_properties, my_match_instance_doc2vec_disambiguations, my_match_instance_doc2vec, my_match_instance_direct
from util_eval import get_mapping_with_type, compute_micro_macro, get_results, find_threshold_by_cross_val

class near_match:
    def __init__(self, label_resource_generator):
        self.lowercased = defaultdict(list)

        for label, resource in label_resource_generator:
            self.lowercased[label.lower()].append((label, resource))

    def get_count_same_cases(self, str_a, str_b):
        count = 0
        for i in range(len(str_a)):
            if (str_a[i].islower() and str_b[i].islower()) or (str_a[i].isupper() and str_b[i].isupper()):
                count += 1
        return count

    def query(self, search):
        search = search.strip()
        candidates = self.lowercased.get(search.lower(), [])
        if len(candidates) == 0:
            return ''
        if len(candidates) == 1:
            return candidates[0][1]

        list_to_sort = [(self.get_count_same_cases(search, original_label), uri) for (original_label, uri) in candidates]
        list_to_sort.sort(key=lambda x: x[0], reverse=True)
        return list_to_sort[0][1]


def __get_label(g, subject, preferred_lang):
    for o in g.objects(subject, RDFS.label):
        if o.language == preferred_lang:
            return o.value
    return g.label(subject)


#create wiki indices

def get_index_wiki_redirects(wiki_tar_file, language):
    redirects_map = dict()
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-transitive-redirects.ttl".format(language))):
            redirects_map[s.value] = o.value
    except KeyError:
        logging.error("could not find file labels.ttl")
    return redirects_map


# create_dbpedia_indices

def get_index_redirects(redirect_path):
    redirects_map = dict()
    with bz2.BZ2File(redirect_path) as redirects_file:
        for sub, pred, obj in parse(redirects_file):
            redirects_map[sub.value] = obj.value
    return redirects_map


def get_index_surface_map(redirect_index, anchor_path):
    surface_map = defaultdict(set)
    with bz2.BZ2File(anchor_path) as anchor_file:
        for s, p, o in parse(anchor_file):
            redirected_subject = redirect_index.get(s.value, s.value)
            label = o.value.strip()
            surface_map[label].add(redirected_subject)
    return surface_map

def get_index_surface_map_test(redirect_index, anchor_path):
    surface_map = defaultdict(set)
    with bz2.BZ2File(anchor_path) as anchor_file:
        i = 0
        for s, p, o in parse(anchor_file):
            redirected_subject = redirect_index.get(s.value, s.value)
            label = o.value.strip()
            surface_map[label].add(redirected_subject)
            i += 1
            if i > 100000:
                break
    return surface_map

def get_index_ontology(ontology_path):
    ontology_graph = Graph()
    ontology_graph.parse(ontology_path, format="nt")
    return ontology_graph


def get_index_properties(redirect_index, onto_index, props_path):
    def read_properties_ontology(redirects_map, ontology_graph):
        for s in set(ontology_graph.subjects(RDF.type, OWL.DatatypeProperty)).union(
                set(ontology_graph.subjects(RDF.type, OWL.ObjectProperty))):
            yield __get_label(ontology_graph, s, "en"), redirects_map.get(str(s), str(s))
            yield s[28:], redirects_map.get(str(s), str(s)) # len("http://dbpedia.org/ontology/") = 28

    def read_properties_file(redirects_map, property_path):
        with bz2.BZ2File(property_path) as properties_file:
            for s, p, o in parse(properties_file):
                redirected_subject = redirects_map.get(s.value, s.value)
                label = o.value.strip()
                yield label, redirected_subject

    match_obj_prop_onto = near_match(read_properties_ontology(redirect_index, onto_index))
    match_obj_prop_file = near_match(read_properties_file(redirect_index, props_path))
    return match_obj_prop_onto, match_obj_prop_file


def get_index_classes(redirect_index, onto_index):
    def read_classes(redirects_map, ontology_graph):
        for s in ontology_graph.subjects(RDF.type, OWL.Class):
            redirected_subject = redirects_map.get(str(s), str(s))
            yield redirected_subject[redirected_subject.rindex('/') + 1:], redirected_subject
            yield __get_label(ontology_graph, s, "en"), redirected_subject
    return near_match(read_classes(redirect_index, onto_index))


def get_index_instances_with_redirects(redirect_index, label_path):
    def read_instances(redirects_map, label_path):
        with bz2.BZ2File(label_path) as label_file:
            for s, p, o in parse(label_file):
                redirected_subject = redirects_map.get(s.value, s.value)
                label = o.value.strip()
                yield label, redirected_subject # s.value
    return near_match(read_instances(redirect_index, label_path))

def get_index_instances_without_redirects(redirect_index, label_path):
    def read_instances(redirects_map, label_path):
        with bz2.BZ2File(label_path) as label_file:
            for s, p, o in parse(label_file):
                if redirects_map.get(s.value, None) is not None:
                    continue # do not use redirects labels
                label = o.value.strip()
                yield label, s.value
    return near_match(read_instances(redirect_index, label_path))

def get_index_disambiguations(disambiguations_path):
    disambiguations = defaultdict(set)
    with bz2.BZ2File(disambiguations_path) as disambiguations_file:
        for s, p, o in parse(disambiguations_file):
            disambiguations[s.value].add(o.value)
    return disambiguations

def get_index_doc2vec(doc2vec_path):
    return Doc2Vec.load(doc2vec_path)





def run_configurations(match_function, domain_to_dump_file, gold_dir, type,find_threshold,indices_dict):
    all_result = []
    mapping_system_list, gold_list = [], []
    for one_eval in glob.glob(gold_dir):
        wiki_domain = os.path.basename(one_eval).split('~')[0]
        wiki_file = domain_to_dump_file.get(wiki_domain, None)
        if wiki_file is None:
            continue

        logging.info(wiki_domain)
        mapping_gold, onto1, onto2, extension = parse_mapping_from_file(one_eval)
        gold_class, gold_property, gold_instance = get_mapping_with_type(mapping_gold)

        # mapping system
        language = os.path.basename(wiki_file).split('~')[1]
        with tarfile.open(wiki_file, 'r', encoding='utf8') as in_tar:
            wiki_redirect_index = get_index_wiki_redirects(in_tar, language)
            indices_dict['wiki_redirect_index'] = wiki_redirect_index
            system_results = match_function(in_tar, language,indices_dict)

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
        logging.info("macro: prec: {} recall: {}  f-measure: {}".format(micro_macro[0][0], micro_macro[0][1], micro_macro[0][2]))
        logging.info("micro: prec: {} recall: {}  f-measure: {}".format(micro_macro[1][0], micro_macro[1][1], micro_macro[1][2]))




def evaluate_dbpedia_mapping():
    dbpedia_base, gold_dir, dump_dir, doc2vec_path = 'dbpedia/2016_10/', 'gold/dbpedia/*.ttl', 'all_files/*.tar.gz', 'model/'

    indices_dict = {}
    logging.info("Loading redirects")
    redirect_index = get_index_redirects(dbpedia_base + 'transitive_redirects_en.ttl.bz2')  # dict()
    #redirect_index = dict()

    #logging.info("Loading disambiguations")
    #indices_dict['disambiguations_index'] = get_index_disambiguations(dbpedia_base + 'disambiguations_en.ttl.bz2')

    #logging.info("Loading surface")
    #indices_dict['surface_index'] = get_index_surface_map(redirect_index, dbpedia_base + 'anchor_text_en.ttl.bz2') # get_index_surface_map_test(redirect_index, anchor_path)

    #logging.info("Loading ontology")
    #ontology_index = get_index_ontology(dbpedia_base + 'dbpedia_2016-10.nt')

    #logging.info("Loading properties")
    #prop_onto_index, prop_file_index = get_index_properties(redirect_index, ontology_index, dbpedia_base + 'infobox_property_definitions_en.ttl.bz2')
    #indices_dict['prop_onto_index'] = prop_onto_index
    #indices_dict['prop_file_index'] = prop_file_index

    #logging.info("Loading classes")
    #indices_dict['classes_index'] = get_index_classes(redirect_index, ontology_index)

    logging.info("Loading instances")
    #instances_with_redirects = get_index_instances_with_redirects(redirect_index, dbpedia_base + 'labels_en.ttl.bz2')
    #instances_without_redirects = get_index_instances_without_redirects(redirect_index, dbpedia_base + 'labels_en.ttl.bz2')
    indices_dict['instances_index'] = get_index_instances_without_redirects(redirect_index, dbpedia_base + 'labels_en.ttl.bz2')

    #logging.info("Loading doc2vec")
    #indices_dict['doc2vec_index'] = get_index_doc2vec(doc2vec_path)
    #doc2vec_short_dbow = get_index_doc2vec(doc2vec_path + 'short-dbow.model')
    #doc2vec_long_dbow = get_index_doc2vec(doc2vec_path + 'long-dbow.model')
    #doc2vec_short_dm = get_index_doc2vec(doc2vec_path + 'short-dm.model')
    #doc2vec_long_dm = get_index_doc2vec(doc2vec_path + 'long-dm.model')


    logging.info("Finished loading")

    domain_to_dump_file = {os.path.basename(wiki_file).split('~')[2]: wiki_file for wiki_file in glob.glob(dump_dir)}

    #logging.info("class")
    #run_configurations(my_match_classes, domain_to_dump_file, gold_dir, 'class', False, indices_dict)
    #logging.info("prop")
    #run_configurations(my_match_properties, domain_to_dump_file, gold_dir, 'prop', False, indices_dict)
    logging.info("simple")
    run_configurations(my_match_instance_direct, domain_to_dump_file, gold_dir, 'inst', False, indices_dict)

    # logging.info("with_redirects, without disambiguation")
    # indices_dict['instances_index'] = instances_with_redirects
    #
    # logging.info("doc2vec_short_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_short_dbow
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_long_dbow
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_short_dm")
    # indices_dict['doc2vec_index'] = doc2vec_short_dm
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dm")
    # indices_dict['doc2vec_index'] = doc2vec_long_dm
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    #
    #
    # logging.info("with_redirects, with disambiguation")
    #
    # logging.info("doc2vec_short_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_short_dbow
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_long_dbow
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_short_dm")
    # indices_dict['doc2vec_index'] = doc2vec_short_dm
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dm")
    # indices_dict['doc2vec_index'] = doc2vec_long_dm
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    #
    #
    # logging.info("without_redirects, without disambiguation")
    # indices_dict['instances_index'] = instances_without_redirects
    #
    # logging.info("doc2vec_short_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_short_dbow
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_long_dbow
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_short_dm")
    # indices_dict['doc2vec_index'] = doc2vec_short_dm
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    # logging.info("doc2vec_long_dm")
    # indices_dict['doc2vec_index'] = doc2vec_long_dm
    # run_configurations(my_match_instance_doc2vec, domain_to_dump_file, gold_dir, 'inst', True, indices_dict)
    #
    # logging.info("without_redirects, with disambiguation")
    #
    # logging.info("doc2vec_short_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_short_dbow
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True,indices_dict)
    # logging.info("doc2vec_long_dbow")
    # indices_dict['doc2vec_index'] = doc2vec_long_dbow
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True,indices_dict)
    # logging.info("doc2vec_short_dm")
    # indices_dict['doc2vec_index'] = doc2vec_short_dm
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True,indices_dict)
    # logging.info("doc2vec_long_dm")
    # indices_dict['doc2vec_index'] = doc2vec_long_dm
    # run_configurations(my_match_instance_doc2vec_disambiguations, domain_to_dump_file, gold_dir, 'inst', True,indices_dict)


####apply

def apply_model_to_one(wiki_file,output_file, indices_dict):
    language = os.path.basename(wiki_file).split('~')[1]
    my_indices = dict(indices_dict)
    with tarfile.open(wiki_file, 'r', encoding='utf8') as in_tar:
        with open(output_file + os.path.basename(wiki_file), 'w') as out_file:
            my_indices['wiki_redirect_index'] = get_index_wiki_redirects(in_tar, language)

            for source, target, relation, confidence in my_match_classes(in_tar, language, my_indices):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}>.\n".format(source, target))

            for source, target, relation, confidence in my_match_properties(in_tar, language, my_indices):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}>.\n".format(source, target))

            #for source, target, relation, confidence in my_match_instance_doc2vec_disambiguations(in_tar, language, my_indices):
            #    if confidence > 0.5:
            #        out_file.write("<{}> <http://www.w3.org/2002/07/owl#sameAs> <{}>.\n".format(source, target))
            for source, target, relation, confidence in my_match_instance_direct(in_tar, language, my_indices):
                out_file.write("<{}> <http://www.w3.org/2002/07/owl#sameAs> <{}>.\n".format(source, target))


def apply_model():
    #import multiprocessing
    #from functools import partial

    dbpedia_base, dump_dir, doc2vec_path = 'dbpedia/2016_10/', 'all_files/*.tar.gz', 'model/'

    indices_dict = {}
    logging.info("Loading redirects")
    redirect_index = get_index_redirects(dbpedia_base + 'transitive_redirects_en.ttl.bz2')  # dict()

    #logging.info("Loading disambiguations")
    #indices_dict['disambiguations_index'] = get_index_disambiguations(dbpedia_base + 'disambiguations_en.ttl.bz2')

    logging.info("Loading ontology")
    ontology_index = get_index_ontology(dbpedia_base + 'dbpedia_2016-10.nt')

    logging.info("Loading properties")
    prop_onto_index, prop_file_index = get_index_properties(redirect_index, ontology_index, dbpedia_base + 'infobox_property_definitions_en.ttl.bz2')
    indices_dict['prop_onto_index'] = prop_onto_index
    indices_dict['prop_file_index'] = prop_file_index

    logging.info("Loading classes")
    indices_dict['classes_index'] = get_index_classes(redirect_index, ontology_index)

    logging.info("Loading instances")
    indices_dict['instances_index'] = get_index_instances_without_redirects(redirect_index, dbpedia_base + 'labels_en.ttl.bz2')

    #logging.info("Loading doc2vec")
    #indices_dict['doc2vec_index'] = get_index_doc2vec(doc2vec_path + 'long-dbow.model')

    #pool = multiprocessing.Pool(processes=16)
    #prod_x =
    #results = pool.imap(partial(process_one_item, y=10), items.values())

    for wiki_file in glob.glob(dump_dir):
        apply_model_to_one(wiki_file, '/home/shertlin-tmp/dbkwik_v1/dbpedia_mapping_string_based/', indices_dict)



if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_evaluate.log',filemode='w', level=logging.INFO)
    #evaluate_dbpedia_mapping()
    apply_model()
