from __future__ import division
import glob
import os
import tarfile
import logging
from nparser import parse, Resource
from collections import defaultdict


def count_subjects(tar_file, name):
    stmts = 0
    count_set = set()
    try:
        for s, p, o in parse(tar_file.extractfile(name)):
            count_set.add(s.value)
            stmts += 1
    except KeyError:
        logging.error("could not find file " + name)
    return stmts, len(count_set)

def add_in_out_degreee(in_out_degree, tar_file, names):
    stmts = 0
    for name in names:
        try:
            for s, p, o in parse(tar_file.extractfile(name)):
                stmts += 1
                if o.value.startswith('http://dbkwik.webdatacommons.org/'):
                    in_out_degree[o.value][0] += 1
                in_out_degree[s.value][1] += 1  # out degree
        except KeyError:
            logging.error("could not find file " + name)
    return stmts

def add_out_degree(in_out_degree, tar_file, names):
    stmts = 0
    for name in names:
        try:
            for s, p, o in parse(tar_file.extractfile(name)):
                in_out_degree[s.value][1] += 1
                stmts += 1
        except KeyError:
            logging.error("could not find file " + name)
    return stmts

def analysis_before(dump_path):
    instances = 0
    typed_instances = 0
    in_degree = 0
    out_degree = 0
    axioms = 0
    classes = 0
    relations = 0
    for f in sorted(glob.glob(dump_path)): # from natsort import natsorted
        logging.info(f)

        language = os.path.basename(f).split('~')[1]
        with tarfile.open(f, encoding='utf8') as tar:
            in_out_degree = defaultdict(lambda: [0, 0])
            prop_stmt = add_in_out_degreee(in_out_degree, tar, ["{}wiki-20170801-infobox-properties.ttl".format(language)])
            multi_file_stmt = add_out_degree(in_out_degree, tar, ["{}wiki-20170801-labels.ttl".format(language),
                                                "{}wiki-20170801-article-categories.ttl".format(language),
                                                "{}wiki-20170801-homepages.ttl".format(language),
                                                "{}wiki-20170801-template-type.ttl".format(language),
                                                "{}wiki-20170801-short-abstracts.ttl".format(language),
                                                "{}wiki-20170801-long-abstracts.ttl".format(language)])
            class_stmt, number_of_classes = count_subjects(tar, "{}wiki-20170801-template-type-definitions.ttl".format(language))
            classes += number_of_classes

            relation_stmt, number_of_relations = count_subjects(tar, "{}wiki-20170801-infobox-property-definitions.ttl".format(language))
            relations += number_of_relations

            for tmp_in_degree, tmp_out_degree in in_out_degree.values():
                in_degree +=tmp_in_degree
                out_degree += tmp_out_degree

            instances += len(in_out_degree.keys())
            axioms += prop_stmt + multi_file_stmt + class_stmt + relation_stmt

            typed_instance_stmt, number_of_typed_instances = count_subjects(tar,"{}wiki-20170801-template-type.ttl".format(language))
            typed_instances += number_of_typed_instances

    print("instances: {}".format(instances))
    print("typed_instances: {}".format(typed_instances))
    print("in_degree: {}".format(in_degree / instances))
    print("out_degree: {}".format(out_degree / instances))
    print("axioms: {}".format(axioms))
    print("classes: {}".format(classes))
    print("relations: {}".format(relations))

# instances: 14212535
# typed_instances: 1880189
# in_degree: 0.6235817888926922
# out_degree: 7.505852263512455
# axioms: 107833322
# classes: 71580
# relations: 506487



#analysis after

def count_subjects_folder(path, name):
    stmts = 0
    count_set = set()
    try:
        with open(path + name, 'rb') as f:
            for s, p, o in parse(f):
                count_set.add(s.value)
                stmts += 1
    except KeyError:
        logging.error("could not find file " + name)
    return stmts, len(count_set)

def count_unique_types(path):
    types = defaultdict(set)
    try:
        with open(path + 'template-type.ttl', 'rb') as f:
            for s, p, o in parse(f):
                types[s.value].add(o.value)
    except KeyError:
        logging.error("could not find file " + name)
    return sum([len(i) for i in types.values()])


def add_in_out_degreee_folder(in_out_degree, path, names):
    stmts = 0
    for name in names:
        with open(path + name, 'rb') as f:
            for s, p, o in parse(f):
                stmts += 1
                if type(o) == Resource:
                    in_out_degree[o.value][0] += 1
                in_out_degree[s.value][1] += 1  # out degree
    return stmts

def add_out_degree_folder(in_out_degree, path, names):
    stmts = 0
    for name in names:
        with open(path + name, 'rb') as f:
            for s, p, o in parse(f):
                in_out_degree[s.value][1] += 1
                stmts += 1
    return stmts

def analysis_after(dump_path):
    instances = 0
    typed_instances = 0
    count_types = 0
    in_degree = 0
    out_degree = 0
    axioms = 0
    classes = 0
    relations = 0

    language = 'en'
    in_out_degree = defaultdict(lambda: [0, 0])
    prop_stmt = add_in_out_degreee_folder(in_out_degree, dump_path, ["infobox-properties.ttl"])
    multi_file_stmt = add_out_degree_folder(in_out_degree, dump_path, ["labels.ttl","article-categories.ttl",
                                        "homepages.ttl", "template-type.ttl", "short-abstracts.ttl", "long-abstracts.ttl"])
    class_stmt, number_of_classes = count_subjects_folder(dump_path, "template-type-definitions.ttl")
    classes += number_of_classes

    relation_stmt, number_of_relations = count_subjects_folder(dump_path, "infobox-property-definitions.ttl")
    relations += number_of_relations

    for tmp_in_degree, tmp_out_degree in in_out_degree.values():
        in_degree +=tmp_in_degree
        out_degree += tmp_out_degree

    instances += len(in_out_degree.keys())
    axioms += prop_stmt + multi_file_stmt + class_stmt + relation_stmt

    typed_instance_stmt, number_of_typed_instances = count_subjects_folder(dump_path,"template-type.ttl")
    typed_instances += number_of_typed_instances

    count_types += count_unique_types(dump_path)

    print("instances: {}".format(instances))
    print("typed_instances: {}".format(typed_instances))
    print("unique types for all inst: {}".format(count_types))
    print("in_degree: {}".format(in_degree / instances))
    print("out_degree: {}".format(out_degree / instances))
    print("axioms: {}".format(axioms))
    print("classes: {}".format(classes))
    print("relations: {}".format(relations))



if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_mapping.log', filemode='w',level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    #analysis_before('*.tar.gz')
    analysis_after('sorted')
