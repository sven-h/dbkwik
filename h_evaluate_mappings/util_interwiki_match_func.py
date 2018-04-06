from nparser import parse
from scipy import spatial
import operator
import logging

def my_match_classes(wiki_tar_file, language, mapping_index, domain, wiki_redirect_index):
    match_content = []
    classes_index = mapping_index.get_class_index()
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-template-type-definitions.ttl".format(language))):
            if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                match = classes_index.query(o.value, own_domain = domain)
                for class_to_match in match.get('unique', []):
                    match_content.append((s.value, class_to_match, '=', 1.0))
    except KeyError:
        logging.error("could not find file template-type-definitions.ttl")
    return match_content

def my_match_properties(wiki_tar_file, language, mapping_index, domain, wiki_redirect_index):
    match_content = []
    property_index = mapping_index.get_property_index()
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-infobox-property-definitions.ttl".format(language))):
            if p.value == 'http://www.w3.org/2000/01/rdf-schema#label':
                match = property_index.query(o.value, own_domain = domain)
                for prop_to_match in match.get('unique', []):
                    match_content.append((s.value, prop_to_match, '=', 1.0))
    except KeyError:
        logging.error("could not find file infobox-property-definitions.ttl")
    return match_content


def my_match_instance_direct(wiki_tar_file, language, mapping_index, domain, wiki_redirect_index):
    match_content = []
    instances_index = mapping_index.get_instance_index()
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
            if wiki_redirect_index.get(s.value, None) is not None:
                continue # we dont match pages which redirects to somewhere
            match = instances_index.query(o.value, own_domain = domain)
            for inst_to_match in match.get('unique', []):
                match_content.append((s.value, inst_to_match, '=', 1.0))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content


def my_match_instance_doc2vec(wiki_tar_file, language, mapping_index, domain, wiki_redirect_index):
    instances_index = mapping_index.get_instance_index()
    doc2vec_index = mapping_index.get_doc2vec_index()

    match_content = []
    try:
        for s, p, o in parse(wiki_tar_file.extractfile("{}wiki-20170801-labels.ttl".format(language))):
            if wiki_redirect_index.get(s.value, None) is not None:
                continue  # we dont match pages which redirects to somewhere

            try:
                source_vector = doc2vec_index.docvecs[s.value]
            except KeyError:
                source_vector = None

            match = instances_index.query(o.value, False, own_domain=domain)
            for domain, label_resource_list in match.items():
                if domain == 'unique':
                    if source_vector is None:
                        for resource in label_resource_list:
                            match_content.append((s.value, resource, '=', 1.0))
                    else:
                        for resource in label_resource_list:
                            try:
                                confidence = 1 - spatial.distance.cosine(source_vector,doc2vec_index.docvecs[resource])
                            except KeyError:
                                confidence = 1.0
                            match_content.append((s.value, resource, '=', confidence))
                else:
                    #choose one out of the resource list
                    if source_vector is None:
                        continue
                    else:
                        candidates_with_threshold = []
                        for (label, resource) in label_resource_list:
                            try:
                                candidates_with_threshold.append((1 - spatial.distance.cosine(source_vector, doc2vec_index.docvecs[resource]), resource))
                            except KeyError:
                                continue
                        if len(candidates_with_threshold) > 0:
                            max_element = max(candidates_with_threshold, key=operator.itemgetter(0))
                            match_content.append((s.value, max_element[1], '=', max_element[0]))
    except KeyError:
        logging.error("could not find file labels.ttl")
    return match_content