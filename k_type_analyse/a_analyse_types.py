import logging
from nparser import parse
from collections import defaultdict, Counter
import csv



def analyse(dump_dir, out_dir):

    labels = defaultdict(set)
    with open(dump_dir + "template-type-definitions.ttl", 'rb') as f:
        for s, p, o in parse(f):
            if p.value == 'http://www.w3.org/2000/01/rdf-schema#label' and o.extension == '@en':
                labels[s.value].add(o.value)

    type_counter = Counter()
    with open(dump_dir + "template-type.ttl", 'rb') as f:
        for s, p, o in parse(f):
            type_counter[o.value] += 1

    with open(dump_dir + "sd-types-light.ttl", 'rb') as f:
        for s, p, o in parse(f):
            type_counter[o.value] += 1

    with open(dump_dir + "materialized_subclass.ttl", 'rb') as f:
        for s, p, o in parse(f):
            type_counter[o.value] += 1

    with open(out_dir + "type_analyse.csv", 'w') as f:
        writer = csv.writer(f)
        for key, value in type_counter.most_common(None):
            label_set = labels.get(key, set())
            if len(label_set) == 0:
                label_set.add('No label')
            writer.writerow([next(iter(label_set)), value])





if __name__ == "__main__":
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_mapping.log', filemode='w',level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    analyse('sorted/', './')
