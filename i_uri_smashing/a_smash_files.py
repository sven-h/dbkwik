import glob
import os
import tarfile
import logging
import hashlib
import base64
import random
import io

from nparser import parse, Resource, Literal

from multiprocessing import Pool


class sameAsSet(set):
    def __init__(self):
        self.canonicalURI = None

    def getCanonicalURI(self):
        #caching here works because we fill the sameAsMap first and afterwards call getCanonicalURI
        if self.canonicalURI is not None:
            return self.canonicalURI
        else:
            m = hashlib.md5()
            for e in self:
                m.update(e)#.encode('utf-8')
            #print("Compute hash")
            #print(m.digest())
            #print(base64.urlsafe_b64encode(m.digest()))
            self.canonicalURI = base64.urlsafe_b64encode(m.digest())#.decode('utf-8')
            return self.canonicalURI



class sameAsMap():

    def __init__(self):
        self.sameAsSets = dict()

    #@profile
    def add(self, a, b):
        result_a = self.sameAsSets.get(a, None)
        result_b = self.sameAsSets.get(b, None)

        if result_a is not None and result_b is not None:
            if result_a is not result_b:
            #if result_a != result_b:
                #create union by transferring all values from b to a:
                for value in result_b:
                    result_a.add(value)
                    self.sameAsSets[value] = result_a
        elif result_a is None and result_b is None:
            my_new_set = sameAsSet()
            my_new_set.add(a)
            my_new_set.add(b)
            self.sameAsSets[a] = my_new_set
            self.sameAsSets[b] = my_new_set
        else:
            if result_a is not None:
                result_a.add(b)
                self.sameAsSets[b] = result_a
            else:
                result_b.add(a)
                self.sameAsSets[a] = result_b

    def getCanonicalURI(self, element):
        sameas_set_result = self.sameAsSets.get(element, None)
        if sameas_set_result is None:
            #if element.startswith('http://dbkwik.webdatacommons.org/'):
            return base64.urlsafe_b64encode(hashlib.md5(element).digest())#.decode('utf-8')
        else:
            return sameas_set_result.getCanonicalURI()

    def __str__(self):
        return str(self.sameAsSets)

    def get_same_as_sets(self):
        #sameas_sets = set()
        #for value in self.sameAsSets.values():
        #    sameas_sets.add(frozenset(value))
        #return sameas_sets
        my_list = []
        already_seen = set()
        for value in self.sameAsSets.values():
            if id(value) not in already_seen:
                already_seen.add(id(value))
                my_list.append(value)
        return my_list

    def remove_sets_larger_than(self, count):

        for same_as_set in self.get_same_as_sets():
            if len(same_as_set) > count:
                for key in same_as_set:
                    self.sameAsSets.pop(key, None)


    def log_largest_sameas(self):
        logging.info("Largest sets")
        for s in sorted(self.get_same_as_sets(), key=len, reverse=True)[:5000]:
            if len(s) > 30:
                logging.info("set with {} elements represent through {}: {}".format(len(s), s.getCanonicalURI(), random.sample(s, 20)))#.encode('utf-8')
            else:
                logging.info("set with {} elements represent through {}: {}".format(len(s), s.getCanonicalURI(), s))#.encode('utf-8')




def apply_smash_index(smash_index, dump_path, add_files, out_dir):

    only_subject_replacement = set(['anchor-text.ttl', 'category-labels.ttl', #'external-links.ttl',
                                    'homepages.ttl', 'infobox-property-definitions.ttl', 'labels.ttl',
                                    'long-abstracts.ttl', #'out-degree.ttl', 'page-ids.ttl', 'page-length.ttl',
                                    'short-abstracts.ttl', 'template-type-definitions.ttl'])
    only_subject_object_replacement = set(['article-categories.ttl', 'article-templates.ttl',
                                            'article-templates-nested.ttl', 'disambiguations.ttl', #'page-links.ttl',
                                            'template-type.ttl'])
    all_replacement = set(['infobox-properties.ttl'])
    
    all_replacement_names = set().union(only_subject_replacement, only_subject_object_replacement, all_replacement)
    # equations.ttl infobox-test.ttl raw-tables.ttl
    # images.ttl skos-categories.ttl template-type.ttl template-type-definitions.ttl topical-concepts.ttl  wikipedia-links.ttl?
    # interlanguage-links.ttl redirects.ttl -> remove
    # nif?

    for i, wiki_file in enumerate(glob.glob(dump_path)):
        logging.info("Apply index {}".format(i))
        with tarfile.open(wiki_file, encoding='utf8') as tar:
            for name in tar.getnames():
                general_name = '-'.join(name.split('-')[2:])
                if general_name in all_replacement_names:
                    with io.open(out_dir + general_name, 'a', encoding='utf-8') as outfile:
                        member_file = tar.extractfile(name)
                        if general_name in only_subject_replacement:
                            for s, p, o in parse(member_file):
                                if type(s) == Resource:
                                    s.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(s.value)
                                outfile.write((str(s) + " " + str(p) + " " + str(o) + " .\n").decode('utf-8'))
                        elif general_name in only_subject_object_replacement:
                            for s, p, o in parse(member_file):
                                if type(s) == Resource:
                                    s.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(s.value)
                                if type(o) == Resource:
                                    o.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(o.value)
                                outfile.write((str(s) + " " + str(p) + " " + str(o) + " .\n").decode('utf-8'))
                        elif general_name in all_replacement:
                            for s, p, o in parse(member_file):
                                if type(s) == Resource:
                                    s.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(s.value)
                                if type(p) == Resource:
                                    p.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(p.value)
                                if type(o) == Resource:
                                    o.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(o.value)
                                outfile.write((str(s) + " " + str(p) + " " + str(o) + " .\n").decode('utf-8'))
        #if i > 100:
        #    break

    #add files
    for file in glob.glob(add_files):
        with io.open(file, 'rb') as in_file:
            with io.open(out_dir + os.path.basename(file), 'w', encoding='utf-8') as outfile:
                for s, p, o in parse(in_file):
                    if type(s) == Resource:
                        s.value = 'http://dbkwik.webdatacommons.org/resource/' + smash_index.getCanonicalURI(s.value)
                    outfile.write((str(s) + " " + str(p) + " " + str(o) + " .\n").decode('utf-8'))


def build_up_smash_index(dump_path, inter_wiki):
    mysets = sameAsMap()
    #for i, wiki_file in enumerate(glob.glob(dump_path)):
    #    logging.info("Build index with interlanguage links and redirects {} - {}".format(i, wiki_file))
    #    language = os.path.basename(wiki_file).split('~')[1]
    #    with tarfile.open(wiki_file, encoding='utf8') as tar:
    #        try:
    #            interlanguage_file = tar.extractfile("{}wiki-20170801-interlanguage-links.ttl".format(language))
    #            for s, p, o in parse(interlanguage_file):
    #                # print("from {} to {}".format(s, o))
    #                mysets.add(s.value, o.value)
    #        except KeyError:
    #            logging.error("could not find file interlanguage-links.ttl")

            #try:
            #    redirects_file = tar.extractfile("{}wiki-20170801-redirects.ttl".format(language))
            #    for s, p, o in parse(redirects_file):
            #        # print("from {} to {}".format(s, o))
            #        mysets.add(s.value, o.value)
            #except KeyError:
            #    logging.error("could not find file redirects.ttl")
        #if i > 100:
        #    break

    for i, inter_wiki_file in enumerate(glob.glob(inter_wiki)):
        logging.info("Build index with mapping files {} - {}".format(i, inter_wiki_file))
        with open(inter_wiki_file, 'rb') as inter_wiki_mapping:
            for s, p, o in parse(inter_wiki_mapping):
                mysets.add(s.value, o.value)
        #if i > 100:
        #    break
    #with open(inter_wiki, 'rb') as interwiki_mapping:
    #    for s, p, o in parse(interwiki_mapping):
    #        # print("from {} to {}".format(s, o))
    #        mysets.add(s.value, o.value)

    return mysets


def smash():
    #dump_path, inter_wiki, add_files, out_dir = 'files/*.tar.gz', 'mapping/*.tar.gz', '/notexistent/', 'out/'
   
    smash_index = build_up_smash_index(dump_path, inter_wiki)
    smash_index.log_largest_sameas()
    #smash_index.remove_sets_larger_than(12000)
    #apply_smash_index(smash_index, dump_path, add_files, out_dir)



if __name__ == "__main__":
    #logging.basicConfig(handlers=[logging.FileHandler('a_smash.log', 'w', 'utf-8')], format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_smash_string_no_lang_links_new.log', filemode='w', level=logging.INFO)
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    smash()
    #test()