import boto3
import ujson
from lxml import etree as ET
#import xml.etree.ElementTree as ET
from collections import defaultdict
import logging

def __parse_requester_annotation(annotation):
    req_annotation = {}
    for x in annotation.split(';'):
        if len(x) > 0:
            key, value = x.split(':')
            req_annotation[key] = value
    return req_annotation


def __get_HITs(client, type_id=None, batch_id=None, max_results_per_iteration = 100):
    matching_hits = []
    all_hits = client.list_hits(MaxResults=max_results_per_iteration)
    while True:
        for hit in all_hits['HITs']:
            if type_id is not None:
                if type_id != hit['HITTypeId']:
                    continue
            if batch_id is not None:
                req_anno = __parse_requester_annotation(hit['RequesterAnnotation'])
                if req_anno['BatchId'] != batch_id:
                    continue
            matching_hits.append(hit)
        if 'NextToken' not in all_hits:
            break
        all_hits = client.list_hits(NextToken=all_hits['NextToken'], MaxResults=max_results_per_iteration)
    return matching_hits


def __get_assignments_for_hits(client, hit_ids, max_results_per_iteration = 100):
    all_assignments = []
    for hit_id in hit_ids:
        assignments = client.list_assignments_for_hit(HITId=hit_id, MaxResults=max_results_per_iteration)
        while True:
            all_assignments.extend(assignments['Assignments'])
            if 'NextToken' not in assignments:
                break
            assignments = client.list_assignments_for_hit(HITId=hit_id, NextToken=assignments['NextToken'], MaxResults=max_results_per_iteration)
    return all_assignments


def __parse_answers_from_assignments(assignments):
    answer_collection = defaultdict(list)
    nsmap = {'aws': 'http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd'}
    for assignment in assignments:
        answers_string = assignment['Answer']
        #print(answers_string)
        answers_root = ET.fromstring(answers_string.encode('UTF-8'))
        for answer in answers_root.findall('aws:Answer', nsmap):
            question_id = answer.find('aws:QuestionIdentifier', nsmap).text
            free_text = answer.find('aws:FreeText', nsmap).text
            answer_collection[question_id].append(free_text)
    return answer_collection


def get_answers_from_mturk_hits(type_id=None, batch_id=None):
    client = boto3.client('mturk')
    filtered_hits = __get_HITs(client, type_id, batch_id)
    filtered_hits_ids = [hit['HITId'] for hit in filtered_hits]
    all_assignments = __get_assignments_for_hits(client, filtered_hits_ids)
    all_answers = __parse_answers_from_assignments(all_assignments)

    #print(all_answers)
    return all_answers

def get_question_answer_from_mturk_hits(type_id=None, batch_id=None):
    client = boto3.client('mturk')
    filtered_hits = __get_HITs(client, type_id, batch_id)
    filtered_hits_ids = [hit['HITId'] for hit in filtered_hits]
    all_assignments = __get_assignments_for_hits(client, filtered_hits_ids)

    answer_collection = defaultdict(list)
    nsmap = {'aws': 'http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd'}
    for assignment in all_assignments:
        assignment_id = assignment['AssignmentId']
        assignment_with_questions = client.get_assignment(AssignmentId=assignment_id)


        print(assignment_with_questions)
        break
        #answers_root = ET.fromstring(answers_string.encode('UTF-8'))
        #for answer in answers_root.findall('aws:Answer', nsmap):
        #    question_id = answer.find('aws:QuestionIdentifier', nsmap).text
        #    free_text = answer.find('aws:FreeText', nsmap).text
        #    answer_collection[question_id].append(free_text)




def download_assignments_and_store_in_file(file_path, type_id=None, batch_id=None):
    client = boto3.client('mturk')
    filtered_hits = __get_HITs(client, type_id, batch_id)
    filtered_hits_ids = [hit['HITId'] for hit in filtered_hits]
    all_assignments = __get_assignments_for_hits(client, filtered_hits_ids)
    with open(file_path, 'w') as file:
        ujson.dump(all_assignments, file)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    #get_answers_from_mturk_hits('30EHNVFQMZD8K68W5BOY0L3M9SXB1Y', '2780831')
    #download_assignments_and_store_in_file('./test.xml', '3WZIO7X3RMSBRXOX6Q990JNHWR7XA1', '3159448')
    get_question_answer_from_mturk_hits('3WZIO7X3RMSBRXOX6Q990JNHWR7XA1', '3159448')