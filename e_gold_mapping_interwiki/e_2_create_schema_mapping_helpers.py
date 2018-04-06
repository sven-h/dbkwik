import logging
import tarfile
import os
from collections import defaultdict
from nparser import parse
import random
import editdistance
from nltk.corpus import wordnet as wn

def get_prop_and_values_dict(wiki_path):
    language = os.path.basename(wiki_path).split('~')[1]
    property = defaultdict(set)
    with tarfile.open(wiki_path, encoding='utf8') as tar:
        try:
            for s, p, o in parse(tar.extractfile("{}wiki-20170801-infobox-properties.ttl".format(language))):
                if '/' in o.value:
                    o.value = o.value[o.value.rindex('/') + 1:]
                property[p.value].add(o.value)
        except KeyError:
            logging.error("could not find file infobox-properties.ttl")
    return property

def get_classes_and_values_dict(wiki_path):
    language = os.path.basename(wiki_path).split('~')[1]
    classes = defaultdict(set)
    with tarfile.open(wiki_path, encoding='utf8') as tar:
        try:
            for s, p, o in parse(tar.extractfile("{}wiki-20170801-template-type.ttl".format(language))):
                if '/' in s.value:
                    s.value = s.value[s.value.rindex('/') + 1:]
                classes[o.value].add(s.value)
        except KeyError:
            logging.error("could not find file template-type-definitions.ttl")
    return classes


def get_max_intersection(one_set, dict_values_as_set):
    max_prop = ''
    max_value = 0
    max_intersect = set()
    sorted_list = sorted([(prop_two, len(one_set.intersection(values_two)), one_set.intersection(values_two)) for prop_two, values_two in dict_values_as_set.items()], key=lambda x: x[1], reverse=True)
    min_value = sorted_list[0][1]
    if min_value == 0:
        return []
    min_list = []
    for prop, intersection_count, intersection in sorted_list:
        if intersection_count == min_value:
            min_list.append((prop, intersection))
        else:
            break
    return min_list

def get_keys_only_with_path(a_dict):
    return [(key[key.rindex('/') + 1:], key) for key in a_dict.keys()]

def string_similar(keyword, possible_set):
    if keyword in possible_set:
        return keyword
    sorted_list = sorted([(uri, editdistance.eval(keyword, word)) for word, uri in possible_set], key=lambda x: x[1])
    min_value = sorted_list[0][1]
    min_list = []
    for keyword, distance in sorted_list:
        if distance == min_value:
            min_list.append((keyword, distance))
        else:
            break
    return min_list


def get_synonyms(text):
    synonyms = set()
    for s in wn.synsets(text):
        for lemma in s.lemmas():
            synonyms.add(lemma.name())
    return synonyms

def same_values(wiki_path_one, wiki_path_two):

    print("Properties:")

    property_one = get_prop_and_values_dict(wiki_path_one)
    property_two = get_prop_and_values_dict(wiki_path_two)

    property_one_string = get_keys_only_with_path(property_one)
    property_two_string = get_keys_only_with_path(property_two)

    for prop_one in random.sample(property_one.keys(), 10):
        print("Property: {}".format(prop_one))
        print("Values: {}".format(property_one[prop_one]))
        only_path = prop_one[prop_one.rindex('/') + 1:]
        for prop_two, intersection in get_max_intersection(property_one[prop_one], property_two):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}> .    Because of intersection ({}): {}".format(prop_one, prop_two,len(intersection), intersection))

        for prop_two, editdistance in string_similar(only_path, property_two_string):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}> .    Because of edit {} - {}".format(prop_one, prop_two, editdistance, property_two[prop_two]))
        print("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <null> .    Just null".format(prop_one))
        print("\n")

    print("Switch directions")
    print("\n\n")

    for prop_two in random.sample(property_two.keys(), 10):
        print("Property: {}".format(prop_two))
        print("Values: {}".format(property_two[prop_two]))
        only_path = prop_two[prop_two.rindex('/') + 1:]
        for prop_one, intersection in get_max_intersection(property_two[prop_two], property_one):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}> .    Because of intersection ({}): {}".format(prop_one, prop_two,len(intersection),intersection))

        for prop_one, editdistance in string_similar(only_path, property_one_string):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}> .    Because of edit {} - {}".format(prop_one, prop_two, editdistance, property_one[prop_one]))
        print("<null> <http://www.w3.org/2002/07/owl#equivalentProperty> <{}> .    Just null".format(prop_two))
        print("\n")


    print("For searching:")
    print(property_one.keys())
    print(property_two.keys())

    print("\n=======================\nClasses:")

    class_one_dict = get_classes_and_values_dict(wiki_path_one)
    class_two_dict = get_classes_and_values_dict(wiki_path_two)

    class_one_string = get_keys_only_with_path(class_one_dict)
    class_two_string = get_keys_only_with_path(class_two_dict)

    for class_one in class_one_dict.keys(): #random.sample(class_one_dict.keys(), 3):
        print("Class: {}".format(class_one))
        print("Values: {}".format(class_one_dict[class_one]))
        for class_two, intersection in get_max_intersection(class_one_dict[class_one], class_two_dict):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}> .    Because of intersection ({}): {}".format(class_one, class_two,len(intersection),intersection))

        for class_two, editdistance in string_similar(class_one[class_one.rindex('/') + 1:], class_two_string):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}> .    Because of edit {} - {}".format(class_one, class_two, editdistance, class_two_dict[class_two]))
        print("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <null> .    Just null".format(class_one))
        print("\n")


    print("Switch directions")
    print("\n\n")

    for class_two in class_two_dict.keys():#random.sample(class_two_dict.keys(), 10):
        print("Class: {}".format(class_two))
        print("Values: {}".format(class_two_dict[class_two]))
        for class_one, intersection in get_max_intersection(class_two_dict[class_two], class_one_dict):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}> .    Because of intersection ({}): {}".format(class_one, class_two,len(intersection),intersection))

        for class_one, editdistance in string_similar(class_two[class_two.rindex('/') + 1:], class_one_string):
            print("<{}> <http://www.w3.org/2002/07/owl#equivalentClass> <{}> .    Because of edit {} - {}".format(class_one, class_two, editdistance, class_one_dict[class_one]))
        print("<null> <http://www.w3.org/2002/07/owl#equivalentClass> <{}> .    Just null".format(class_two))
        print("\n")

    print("For searching:")
    print(class_one_dict.keys())
    print(class_two_dict.keys())





if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='b_select_gold_wikis_based_on_content.log', filemode='w', # filemode='a'
                        level=logging.INFO)
    base = 'dumps/'

    same_values(base + '1267847~en~darkscape~darkscape.wikia.com.tar.gz', base + '691244~en~oldschoolrunescape~oldschoolrunescape.wikia.com.tar.gz')
    #same_values(base + '304~en~runescape~runescape.wikia.com.tar.gz', base + '1267847~en~darkscape~darkscape.wikia.com.tar.gz')
    #same_values(base + '304~en~runescape~runescape.wikia.com.tar.gz', base + '691244~en~oldschoolrunescape~oldschoolrunescape.wikia.com.tar.gz')

    #same_values(base + '330278~en~heykidscomics~heykidscomics.wikia.com.tar.gz', base + '2237~en~dc~dc.wikia.com.tar.gz')
    #same_values(base + '2233~en~marvel~marvel.wikia.com.tar.gz', base + '2237~en~dc~dc.wikia.com.tar.gz')
    #same_values(base + '2233~en~marvel~marvel.wikia.com.tar.gz',base + '330278~en~heykidscomics~heykidscomics.wikia.com.tar.gz')

    #same_values(base + '113~en~memory-alpha~memory-alpha.wikia.com.tar.gz', base + '323~en~memory-beta~memory-beta.wikia.com.tar.gz')
    #same_values(base + '113~en~memory-alpha~memory-alpha.wikia.com.tar.gz', base + '745~en~stexpanded~stexpanded.wikia.com.tar.gz')
    #same_values(base + '323~en~memory-beta~memory-beta.wikia.com.tar.gz', base + '745~en~stexpanded~stexpanded.wikia.com.tar.gz')
