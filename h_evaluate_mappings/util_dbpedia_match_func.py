from nparser import parse
from scipy import spatial
import operator
import logging

def my_match_classes(wiki_tar_file, language, indices_dict):
    match_content = []
    classes_index = indices_dict['classes_index']
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-template-type-definitions.ttl".format(language))):
            if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                match = classes_index.query(o.value).strip()
                if len(match) > 0:
                    match_content.append((s.value, match, '=', 1.0))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content

def my_match_properties(wiki_tar_file, language, indices_dict):
    match_content = []
    match_obj_prop_onto = indices_dict['prop_onto_index']
    match_obj_prop_file = indices_dict['prop_file_index']
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-infobox-property-definitions.ttl".format(language))):
            if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                match = match_obj_prop_onto.query(o.value).strip()
                if len(match) > 0:
                    match_content.append((s.value, match, '=', 1.0))
                else:
                    match = match_obj_prop_file.query(o.value).strip()
                    if len(match) > 0:
                        match_content.append((s.value, match, '=', 1.0))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content


def my_match_instance_direct(wiki_tar_file, language, indices_dict):
    match_content = []
    wiki_redirect_index = indices_dict['wiki_redirect_index']
    instances_index = indices_dict['instances_index']
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
            if wiki_redirect_index.get(s.value, None) is not None:
                continue # we dont match pages which redirects to somewhere
            match = instances_index.query(o.value).strip()
            if len(match) > 0:
                match_content.append((s.value, match, '=', 1.0))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content



def my_match_instance_doc2vec(wiki_tar_file, language, indices_dict):
    wiki_redirect_index = indices_dict['wiki_redirect_index']
    instances_index = indices_dict['instances_index']
    doc2vec_index = indices_dict['doc2vec_index']
    match_content = []
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
            if wiki_redirect_index.get(s.value, None) is not None:
                continue # we dont match pages which redirects to somewhere
            match = instances_index.query(o.value).strip()
            if len(match) > 0:
                try:
                    confidence = 1 - spatial.distance.cosine(doc2vec_index.docvecs[s.value], doc2vec_index.docvecs[match])
                except KeyError:
                    confidence = 1.0
                match_content.append((s.value, match, '=', confidence))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content


def my_match_instance_doc2vec_disambiguations(wiki_tar_file, language, indices_dict):
    wiki_redirect_index = indices_dict['wiki_redirect_index']
    instances_index = indices_dict['instances_index']
    doc2vec_index = indices_dict['doc2vec_index']
    disambiguations_index = indices_dict['disambiguations_index']
    match_content = []
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
            if wiki_redirect_index.get(s.value, None) is not None:
                continue  # we dont match pages which redirects to somewhere
            match = instances_index.query(o.value).strip()
            if len(match) > 0:
                disambiguations = disambiguations_index.get(match, None)
                if disambiguations is None:
                    try:
                        confidence = 1 - spatial.distance.cosine(doc2vec_index.docvecs[s.value], doc2vec_index.docvecs[match])
                    except KeyError:
                        confidence = 1.0
                    match_content.append((s.value, match, '=', confidence))
                else:
                    candidates_with_threshold = []
                    try:
                        source_vec = doc2vec_index.docvecs[s.value]
                    except KeyError:
                        continue  # do not match because we have multiple disambiguations but no possibility to decide

                    for candidate in disambiguations:
                        try:
                            candidates_with_threshold.append((1 - spatial.distance.cosine(source_vec, doc2vec_index.docvecs[candidate]), candidate))
                        except KeyError:
                            continue
                    if len(candidates_with_threshold) > 0:
                        max_element = max(candidates_with_threshold, key=operator.itemgetter(0))
                        match_content.append((s.value, max_element[1], '=', max_element[0]))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content