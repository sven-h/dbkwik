import logging
from collections import defaultdict, Counter
import csv
from AlignmentFormat import serialize_mapping_to_file
from nparser import parse
import glob
import os

#def retrieve_mturk():
    # not possible programatically: see
#from utilmturk import get_answers_from_mturk_hits, download_assignments_and_store_in_file
    #https://stackoverflow.com/questions/35066826/get-the-layout-parameters-for-a-hit-in-mechanical-turk-with-boto
    #test = get_answers_from_mturk_hits('3WZIO7X3RMSBRXOX6Q990JNHWR7XA1', '3155727')

def get_dbkwik_uri_destination(url):
    domain = url[7:url.index('.wikia.com')]
    path = url[url.index('wikia.com/wiki/')+15:]
    resource_uri = 'http://dbkwik.webdatacommons.org/' + domain + '/resource/' + path
    return resource_uri



def get_checked_answers(hits, answer_i, destination_number, domain):
    answers = []
    worker_ids = []
    for hit in hits:
        answer = hit['Answer.{}_mapping_dst{}'.format(answer_i, destination_number)]
        if answer == "no match" or answer.startswith(domain):
            #correct
            answers.append(answer)
            worker_ids.append(hit['WorkerId'])
        else:
            logging.error("Not a correct answer: {}".format(answer))
    return answers, Counter(answers).most_common(1)[0][0], worker_ids


class mapping_data():
    def __init__(self):
        self.mapping = dict()

    def add_mapping(self, domain_one, resource_one, domain_two, resource_two, relation):

        mapping_list = self.mapping.get((domain_one, domain_two), None)
        if mapping_list is not None:
            mapping_list.append((resource_one, resource_two, relation, 1.0))
        else:
            mapping_list = self.mapping.get((domain_two, domain_one), None)
            if mapping_list is not None:
                mapping_list.append((resource_two, resource_one, relation, 1.0))
            else:
                self.mapping[(domain_one, domain_two)] = [(resource_one, resource_two, relation, 1.0)]

    def items(self):
        return self.mapping.items()


def generate_mapping():
    from nltk import agreement

    #https://stackoverflow.com/questions/11528150/inter-rater-agreement-in-python-cohens-kappa
    map_same_hit = defaultdict(list)
    with open('Batch_3159448_batch_results.csv', 'r', encoding='utf-8') as csv_file:
        csr_reader = csv.DictReader(csv_file)
        for row in csr_reader:
            map_same_hit[row['HITId']].append(row)

    agreement_data = []
    mapping = mapping_data()
    for hit_id, hits in map_same_hit.items():

        source_url = hits[0]['Input.domain_src']
        source_domain = source_url[7:source_url.index('.wikia.com')]
        dst_1_url = hits[0]['Input.domain_dst1']
        dst_1_domain = dst_1_url[7:dst_1_url.index('.wikia.com')]
        dst_2_url = hits[0]['Input.domain_dst2']
        dst_2_domain = dst_2_url[7:dst_2_url.index('.wikia.com')]

        if len(hits) == 5:
            print("Hit")
            for i in range(10):

                answers_dst_1, majority_dst_1, worker_ids_1 = get_checked_answers(hits, i, 1, dst_1_url + '/wiki/')
                agreement_data.extend([(str(j), hit_id + '_' + str(i), answers_dst_1[j]) for j in range(5)]) # use autoincrement id for each worker for each task
                #agreement_data.extend([(worker_ids_1[j], hit_id + '_' + str(i), answers_dst_1[j]) for j in range(5)])  # use the worker id from mturk

                answers_dst_2, majority_dst_2, worker_ids_2 = get_checked_answers(hits, i, 2, dst_2_url + '/wiki/')

                resource_src = 'http://dbkwik.webdatacommons.org/' + source_domain + '/resource/' + hits[0]['Input.wiki_{}'.format(i)]

                if majority_dst_1 != "no match":
                    resource_dst_1 = get_dbkwik_uri_destination(majority_dst_1)
                    #print("mapping: {} -> {}".format(resource_src, resource_dst_1))
                    mapping.add_mapping(source_domain, resource_src, dst_1_domain, resource_dst_1, '=')
                else:
                    mapping.add_mapping(source_domain, resource_src, dst_1_domain, 'null', '%')


                if majority_dst_2 != "no match":
                    resource_dst_2 = get_dbkwik_uri_destination(majority_dst_2)
                    #print("mapping: {} -> {}".format(resource_src, resource_dst_2))
                    mapping.add_mapping(source_domain, resource_src, dst_2_domain, resource_dst_2, '=')
                else:
                    mapping.add_mapping(source_domain, resource_src, dst_2_domain, 'null', '%')

                #transitivity
                if majority_dst_1 != "no match" and majority_dst_2 != "no match":
                    #print("mapping transitiv: {} -> {}".format(resource_dst_1, resource_dst_2))
                    mapping.add_mapping(dst_1_domain, resource_dst_1, dst_2_domain, resource_dst_2, '=')
                if majority_dst_1 != "no match" and majority_dst_2 == "no match":
                    mapping.add_mapping(dst_1_domain, resource_dst_1, dst_2_domain, 'null', '%')
                if majority_dst_1 == "no match" and majority_dst_2 != "no match":
                    mapping.add_mapping(dst_2_domain, resource_dst_2, dst_1_domain, 'null', '%')



    agreement_data = sorted(agreement_data, key=lambda x: (x[0], x[1]))
    ratingtask = agreement.AnnotationTask(data=agreement_data)
    print("kappa " + str(ratingtask.kappa()))
    print("fleiss " + str(ratingtask.multi_kappa()))
    print("alpha " + str(ratingtask.alpha()))
    print("scotts " + str(ratingtask.pi()))

    #add schema
    for schema_file in glob.glob('./schema/*'):
        file_split = os.path.basename(schema_file).split('~')
        domain_one = file_split[0]
        domain_two = file_split[1]
        with open(schema_file, 'rb') as f:
            for s,p,o in parse(f):
                if s.value == 'null':
                    mapping.add_mapping(domain_one, 'null', domain_two, o.value, '%')
                if o.value == 'null':
                    mapping.add_mapping(domain_one, s.value, domain_two, 'null', '%')
                if s.value != 'null' and o.value != 'null':
                    mapping.add_mapping(domain_one, s.value, domain_two, o.value, '=')


    for (src_domain, dst_domain), mapping in mapping.items():
        serialize_mapping_to_file('./gold/' + src_domain + '~' + dst_domain+ "~evaluation.xml",
                                  mapping,
                                  (src_domain, 'http://' + src_domain + '.wikia.com'),
                                  (dst_domain, 'http://' + dst_domain + '.wikia.com'))

def rater_agreement_test():
    logging.info("Load agreement")
    from nltk import agreement
    logging.info("Start computing agreement")
    rater1 = [1, 1, 1]
    rater2 = [1, 1, 0]
    rater3 = [0, 1, 1]

    taskdata = [[0, str(i), str(rater1[i])] for i in range(0, 3)] + [[1, str(i), str(rater2[i])] for i in
                                                                     range(0, 3)] + [[2, str(i), str(rater3[i])] for i
                                                                                     in range(0, 3)]

    print(taskdata)
    #taskdata needs to be in format: [(coder1,item1,label), (coder1,item2,label), (coder2,item1,label), (coder2,item2,label) ....]
    #all labels from coder1 first, then all labels from coder2 and so on.

    ratingtask = agreement.AnnotationTask(data=taskdata)
    print("kappa " + str(ratingtask.kappa()))
    print("fleiss " + str(ratingtask.multi_kappa()))
    print("alpha " + str(ratingtask.alpha()))
    print("scotts " + str(ratingtask.pi()))

    #https://en.wikipedia.org/wiki/Inter-rater_reliability
    #https://stackoverflow.com/questions/11528150/inter-rater-agreement-in-python-cohens-kappa
    #http://www.statsmodels.org/dev/generated/statsmodels.stats.inter_rater.fleiss_kappa.html
    #http://scikit-learn.org/stable/modules/classes.html#module-sklearn.metrics
    #https://en.wikibooks.org/wiki/Algorithm_Implementation/Statistics/Fleiss%27_kappa#Python
    #https://gist.github.com/ShinNoNoir/4749548




if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',filename='f_create_mapping_files.log', filemode='w', level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    generate_mapping()
    #test()
    #rater_agreement_test()
