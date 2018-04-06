from __future__ import division
import logging
from collections import defaultdict
#### eval functions

def get_mapping_with_type(mapping):
    class_mapping = []
    property_mapping = []
    resource_mapping = []
    for (source, target, relation, confidence) in mapping:
        if ('/class/' in source or '/ontology/' in source or 'null' in source) and ('/class/' in target or '/ontology/' in target or 'null' in target): # and
            class_mapping.append((source, target, relation, confidence))
        elif ('/property/' in source or '/ontology/' in source or 'null' in source) and ('/property/' in target or '/ontology/' in target or 'null' in target):
            property_mapping.append((source, target, relation, confidence))
        elif ('/resource/' in source or 'null' in source) and ('/resource/' in target or 'null' in target):
            resource_mapping.append((source, target, relation, confidence))
        else:
            logging.error("Wrong mapping")
    return class_mapping, property_mapping, resource_mapping


def compute_micro_macro(list_of_results):
    sum_true_positiv = 0
    sum_predicted_positive = 0
    sum_actual_positive = 0
    sum_recall = 0
    sum_precision = 0
    i = 0
    for (true_positiv, predicted_positive, actual_positive), (precision, recall, fmeasure) in list_of_results:
        i += 1
        sum_true_positiv += true_positiv
        sum_predicted_positive += predicted_positive
        sum_actual_positive += actual_positive
        sum_recall += recall
        sum_precision += precision

    macro_precision = sum_precision / i
    macro_recall = sum_recall / i
    macro_fmeasure = 2 * (macro_precision * macro_recall) / (macro_precision + macro_recall)
    #logging.info("macro: prec: {} recall: {}  f-measure: {}".format(macro_precision, macro_recall, macro_fmeasure))

    if sum_predicted_positive == 0:
        micro_precision = 1.0
    else:
        micro_precision = sum_true_positiv / sum_predicted_positive
    if sum_actual_positive == 0:
        micro_recall = 1.0
    else:
        micro_recall = sum_true_positiv / sum_actual_positive
    micro_fmeasure = 2 * (micro_precision * micro_recall) / (micro_precision + micro_recall)
    #logging.info("micro: prec: {} recall: {}  f-measure: {}".format(micro_precision, micro_recall, micro_fmeasure))

    return (macro_precision, macro_recall, macro_fmeasure), (micro_precision, micro_recall, micro_fmeasure)

def get_results(system, gold, assume_kb_one_no_duplicates=False, assume_kb_two_no_duplicates = False):
    #assume_kb_two_no_duplicates:
    #example: gold: a<->b    and system:  a<->z     if assume_kb_two_no_duplicates is true then we know that a<->z couldn't hold because already a<->b holds
    # assume_kb_one_no_duplicates:
    # example: gold: a<->b    and system:  z<->b     if assume_kb_one_no_duplicates is true then we know that z<->b couldn't hold because already a<->b holds
    #in both cases make sure that there are no a<->b , a<->c    (mappings with same source and different target) or just set ..no_duplicates to False(default)
    system_map_source_target = defaultdict(set)
    system_map_target_source = defaultdict(set)
    for (source, target, relation, confidence) in system:
        if relation == '=':
            system_map_source_target[source].add(target)
            system_map_target_source[target].add(source)

    true_positive = 0
    false_positive = 0
    false_negative = 0
    for (source, target, relation, confidence) in gold:

        if target == 'null':
            false_positive += len(system_map_source_target.get(source, set()))
            if len(system_map_source_target.get(source, set())) > 0:
                logging.debug("too much {} = {}".format(source, system_map_source_target.get(source, set())))
        elif source == 'null':
            false_positive += len(system_map_target_source.get(target, set()))
            if len(system_map_target_source.get(target, set())) > 0:
                logging.debug("too much {} = {}".format(system_map_target_source.get(target, set()), target))
        else:
            result = system_map_source_target.get(source, set())
            if target in result:
               true_positive += 1
               logging.debug("true_positiv {} = {}".format(source, target))
            else:
                false_negative += 1
                logging.debug("not found {} = {}".format(source, target))
                #the correct one is not found - if we assume that KB one has no duplicates, we can punish some of the results
                if assume_kb_one_no_duplicates:
                    false_positive += len(system_map_target_source.get(target, set()))
                    if len(system_map_target_source.get(target, set())) > 0:
                        logging.debug("too much: {} = {}".format(system_map_target_source.get(target, set()), target))
                if assume_kb_two_no_duplicates:
                    false_positive += len(result)
                    if len(result) > 0:
                        logging.debug("too much: {} = {}".format(source, result))

    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative

    if predicted_positive == 0:
        precision = 1
    else:
        precision = true_positive / predicted_positive

    if actual_positive == 0:
        recall = 1
    else:
        recall = true_positive / actual_positive

    if precision == 0 and recall == 0:
        fmeasure = 0
    else:
        fmeasure = 2 * (precision * recall) / (precision + recall)

    return (true_positive, predicted_positive, actual_positive), (precision, recall, fmeasure)


def get_thresholds_from_list_of_mappings(mappings):
    thresholds = set()
    for mapping in mappings:
        for source, target, relation, confidence in mapping:
            thresholds.add(float("{0:.2f}".format(confidence)))
    return thresholds

def __filter_mapping_threshold(mapping, threshold):
    filtered_mapping = []
    for source, target, relation, confidence in mapping:
        if confidence >= threshold:
            filtered_mapping.append((source, target, relation, confidence))
    return filtered_mapping


def filter_mapping_domain(mapping, domain_start):
    filtered_mapping = []
    for source, target, relation, confidence in mapping:
        if target.startswith(domain_start):
            filtered_mapping.append((source, target, relation, confidence))
    return filtered_mapping

def find_threshold_by_cross_val(system_mappings, gold_mappings):
    if len(system_mappings) != len(gold_mappings):
        logging.error("len(system_mappings) != len(gold_mappings)")
        return

    #we actually do a leave one out here
    cv_results = []
    for i in range(len(system_mappings)):
        train_mappings = [system_mappings[j] for j in range(len(system_mappings)) if j != i]
        train_gold = [gold_mappings[j] for j in range(len(gold_mappings)) if j != i]

        test_mapping = system_mappings[i]
        test_gold = gold_mappings[i]

        threshold_results_list = []
        possible_thresholds = get_thresholds_from_list_of_mappings(train_mappings)
        for threshold in possible_thresholds:

            train_results = []
            for k in range(len(train_mappings)):
                train_results.append(get_results(__filter_mapping_threshold(train_mappings[k], threshold), train_gold[k], True, True))
            threshold_results_list.append((threshold, compute_micro_macro(train_results)))

        max_element = max(threshold_results_list, key=lambda x: x[1][0][2])# choose macro f-measure (= [0][2] )
        choosen_threshold = max_element[0]
        logging.info("Choosen threshold for round {} is {}".format(i, choosen_threshold))

        cv_results.append(get_results(__filter_mapping_threshold(test_mapping, choosen_threshold), test_gold, True, True))

    micro_macro = compute_micro_macro(cv_results)
    logging.info("macro: prec: {} recall: {}  f-measure: {}".format(micro_macro[0][0], micro_macro[0][1], micro_macro[0][2]))
    logging.info("micro: prec: {} recall: {}  f-measure: {}".format(micro_macro[1][0], micro_macro[1][1], micro_macro[1][2]))

