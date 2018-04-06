from __future__ import division
import logging
from collections import defaultdict
from collections import Counter
from nparser import parse, Resource
import operator
import bz2
from itertools import combinations
from rdflib import Graph, RDFS

def extract_domain_range_type(folder_path, language):
    type_map = defaultdict(lambda : 'http://www.w3.org/2002/07/owl#Thing')
    #with open(folder_path + '{}wiki-20170801-template-type.ttl'.format(language), 'rb')as template_file:
    with open(folder_path + 'template-type.ttl', 'rb')as template_file:
        for s,p,o in parse(template_file):
            type_map[s.value] = o.value

    domain = defaultdict(lambda :defaultdict(int))
    range = defaultdict(lambda: defaultdict(int))
    untyped = defaultdict(set)
    #with open(folder_path + '{}wiki-20170801-infobox-properties.ttl'.format(language), 'rb')as template_file:
    with open(folder_path + 'infobox-properties.ttl', 'rb')as template_file:
        for s,p,o in parse(template_file):
            domain[p.value][type_map[s.value]] += 1
            if type(o) == Resource:
                type_object = type_map[o.value]
                range[p.value][type_object] += 1
                if type_object != 'http://www.w3.org/2002/07/owl#Thing' and o.value.startswith('http://dbkwik.webdatacommons.org'):
                    untyped[o.value].add(p.value)
            else:
                range[p.value]['http://www.w3.org/2000/01/rdf-schema#Literal'] += 1

    domain_count = 0
    range_count = 0
    with open(folder_path + 'property-restrictions.ttl', 'w') as types_out:#, encoding='utf-8'
        for prop in set(domain.keys()).union(range.keys()):
            max_domain = max(domain[prop].items(), key=operator.itemgetter(1))[0]
            if max_domain != 'http://www.w3.org/2002/07/owl#Thing':
                types_out.write('<{}> <http://www.w3.org/2000/01/rdf-schema#domain> <{}> .\n'.format(prop, max_domain))
                domain_count += 1
            max_range = max(range[prop].items(),key=operator.itemgetter(1))[0]
            if max_range != 'http://www.w3.org/2002/07/owl#Thing':
                types_out.write('<{}> <http://www.w3.org/2000/01/rdf-schema#range> <{}> .\n'.format(prop,max_range))
                range_count += 1
    logging.info("Domain restrictions: {}".format(domain_count))
    logging.info("Range restrictions: {}".format(range_count))


    with open(folder_path + 'sd-types-light.ttl', 'w') as types_out:#, encoding='utf-8'
        for object_uri, in_props in untyped.items():
            allrangeTypes = defaultdict(int)
            for in_prop in in_props:
                max_type = max(range[in_prop].items(), key=operator.itemgetter(1))[0]
                if max_type != 'http://www.w3.org/2002/07/owl#Thing' and max_type != 'http://www.w3.org/2000/01/rdf-schema#Literal':
                    allrangeTypes[max_type] += 1
            if len(allrangeTypes) > 0:
                types_out.write('<{}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{}> .\n'.format(object_uri,max(allrangeTypes.items(),key=operator.itemgetter(1))[0]))



def __compute_transitive_closure(mydict):
    trans_closure = defaultdict(set)
    for key in mydict.keys():
        next_higher_class = set([key])
        while len(next_higher_class) > 0:
            tmp_next_higher = set()
            for next_higher in next_higher_class:
                tmp_next_higher.update(mydict.get(next_higher, set()))
            trans_closure[key].update(tmp_next_higher)
            next_higher_class = tmp_next_higher
    return trans_closure

def extract_all_dbpedia_subclasses(onto_path):
    sub_class_of = defaultdict(set)
    g = Graph()
    g.parse(onto_path, format="nt")
    for s, o in g.subject_objects(RDFS.subClassOf):
        str_s, str_o = str(s), str(o)
        if str_s.startswith('http://dbpedia.org/ontology/') and str_o.startswith('http://dbpedia.org/ontology/'):
            sub_class_of[str_s].add(str_o)
    trans_closure = __compute_transitive_closure(sub_class_of)
    return trans_closure



def read_mapping_dbkwik_dbpedia(folder_path, file_name):
    mapping = defaultdict(set)
    with open(folder_path + file_name, 'rb')as template_file:
        for s, p, o in parse(template_file):
            mapping[s.value].add(o.value)
    return mapping

def has_subclass_relation(a, b, mapping_dbkwik_dbpedia, dbpedia_subclass_dict):
    for a_dbpedia_resource in mapping_dbkwik_dbpedia.get(a, set()):
        a_dbpedia_resource_superclasses = dbpedia_subclass_dict.get(a_dbpedia_resource, set())
        b_dbpedia_resources = dbpedia_subclass_dict.get(b, set())
        if len(a_dbpedia_resource_superclasses.intersection(b_dbpedia_resources)) > 0:
            print("found {} subclass {}".format(a_dbpedia_resource, b_dbpedia_resources))
            return True
    return False



def extract_subclass(folder_path, dbpedia_path):
    instance_to_types = defaultdict(set)
    single_type_count = defaultdict(int)
    ##with bz2.open('instance_types_en.ttl.bz2', 'rb') as template_file:
    with open(folder_path + 'template-type.ttl', 'rb')as template_file:
        for s, p, o in parse(template_file):
            single_type_count[o.value] +=1
            instance_to_types[s.value].add(o.value)

    intersection_map = defaultdict(int)
    for instance, types in instance_to_types.items():
        if len(types) > 2:
            for a,b in combinations(sorted(types), 2):
                intersection_map[(a,b)] += 1

    labels = dict()
    with open(folder_path + 'template-type-definitions.ttl', 'rb')as template_file:
        for s, p, o in parse(template_file):
            labels[s.value] = o.value

    elements = []
    subclassof_map = defaultdict(set)
    for (a, b), len_intersection in intersection_map.items():
        #print(len_intersection / single_type_count[a])
        if (len_intersection / single_type_count[a]) > 0.95:
            elements.append((a, b, len_intersection / single_type_count[a], labels[a], labels[b]))
            subclassof_map[a].add(b)
        #print(len_intersection / single_type_count[b])
        if (len_intersection / single_type_count[b]) >= 0.95:
            elements.append((b, a, len_intersection / single_type_count[b], labels[b], labels[a]))
            subclassof_map[b].add(a)
    elements = sorted(elements, key=operator.itemgetter(2), reverse=True)

    with open(folder_path + 'subclass.ttl', 'w') as subclass_file: # , encoding='utf-8'
        for a,b,t,la,lb in elements:
            subclass_file.write("<{}> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <{}>. # {} : <<{}>> subclass of <<{}>>\n".format(a,b,t,la,lb))

    #materialize subclass of
    with open(folder_path + 'materialized_subclass.ttl', 'w') as materialized_subclass_file:  # , encoding='utf-8'
        for instance, types in instance_to_types.items():
            for type in types:
                for add_type in subclassof_map.get(type, set()):
                    if add_type not in types:
                        materialized_subclass_file.write(("<{}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{}>.\n".format(instance, add_type)))

    #use dbpedia to find the correct threshold:
    #dbpedia_subclass_dict = extract_all_dbpedia_subclasses(dbpedia_path + 'dbpedia_2016-10.nt')
    #mapping_dbkwik_dbpedia = read_mapping_dbkwik_dbpedia(folder_path, 'dbpedia_mapping_doc2vec.txt')
    #positive_example = []
    #for (a, b), len_intersection in intersection_map.items():
    #    if has_subclass_relation(a, b, mapping_dbkwik_dbpedia, dbpedia_subclass_dict):
    #        positive_example.append((a,b, len_intersection / single_type_count[a]))
    #    if has_subclass_relation(b, a, mapping_dbkwik_dbpedia, dbpedia_subclass_dict):
    #        positive_example.append((b,a, len_intersection / single_type_count[b]))



def main():
    extract_domain_range_type('sorted/', '')
    extract_subclass('sorted/', '')
    
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='test.log', filemode='w',
                        level=logging.DEBUG)
    main()