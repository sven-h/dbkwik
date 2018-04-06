import logging
import ujson
import gensim
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
import gzip
import multiprocessing

class JsonLineCorpus(object):

    def __init__(self, corpus_path):
        self.corpus_path = corpus_path

    def __iter__(self):
        with gzip.open(self.corpus_path, 'r') as fin:
            for line in fin:
                obj = ujson.loads(line)
                yield TaggedDocument(obj[1].split(), [obj[0]])


class JsonLineMemoryCorpus(object):

    def __init__(self, corpus_path):
        self.corpus_path = corpus_path
        self.array = []
        logging.info("Start loading file")
        with gzip.open(self.corpus_path, 'r') as fin:
            for line in fin:
                obj = ujson.loads(line)
                self.array.append(TaggedDocument(obj[1].split(), [obj[0]]))
        logging.info("Finished loading file")


    def __iter__(self):
        for doc in self.array:
            yield doc



def train_model(corpus_path, out_path, name):
    #https://github.com/RaRe-Technologies/gensim/blob/develop/docs/notebooks/doc2vec-IMDB.ipynb
    cores = multiprocessing.cpu_count()

    logging.info("doc2vec Fast version: {}".format(gensim.models.doc2vec.FAST_VERSION))
    logging.info("cores: {}".format(cores))

    assert gensim.models.doc2vec.FAST_VERSION > -1, "This will be painfully slow otherwise"

    corpus = JsonLineCorpus(corpus_path)#JsonLineMemoryCorpus(corpus_path)
    d2v_model_dbow = Doc2Vec(dm=0, epochs=20, workers=cores)# PV-DBOW
    d2v_model_dbow.build_vocab(corpus)

    d2v_model_dm = Doc2Vec(dm=1, epochs=20, workers=cores)  # PV-DM
    d2v_model_dm.reset_from(d2v_model_dbow)# d2v_model_dm.build_vocab(corpus)

    d2v_model_dbow.train(corpus, total_examples=d2v_model_dbow.corpus_count, epochs=20)
    d2v_model_dbow.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
    d2v_model_dbow.save(out_path + name + '-dbow.model')

    d2v_model_dm.train(corpus, total_examples=d2v_model_dm.corpus_count, epochs=20)
    d2v_model_dm.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
    d2v_model_dm.save(out_path + name + '-dm.model')


def writeJsonLines(out_path, dbpedia_redirects, dbpedia_abstract_path, abstracts_path_ending='long-abstracts'):
    from nparser import parse
    from natsort import natsorted
    import tarfile
    import bz2
    import os
    import glob

    logging.info("Load dbpedia redirects")
    redirects = dict()
    with bz2.open(dbpedia_redirects) as redirects_file:
        for sub, pred, obj in parse(redirects_file):
            redirects[sub.value] = obj.value


    with gzip.open(out_path, 'w') as outf:

        logging.info("process dbpedia abstracts")
        with bz2.open(dbpedia_abstract_path) as abstract_file:
            for s, p, o in parse(abstract_file):
                subject = redirects.get(s.value, s.value)
                outf.write((ujson.dumps([subject, o.value]) + '\n').encode('utf-8'))

        logging.info("process dbkwik abstracts")
        #for fname in glob.glob('dumps\\*.tar.gz'):
        for fname in natsorted(os.listdir('D:\\2018_01_31_results_dbkwik_uni_run\\dbkwik-v1.0')):
            fname = os.path.join('D:\\2018_01_31_results_dbkwik_uni_run\\dbkwik-v1.0', fname)

            context = os.path.basename(fname).split('~')
            language = context[1]
            logging.info("process " + fname)
            with tarfile.open(fname, encoding='utf8') as tar:
                try:
                    abstracts_file = tar.extractfile("{}wiki-20170801-{}.ttl".format(language, abstracts_path_ending))
                    for s, p, o in parse(abstracts_file):
                        outf.write((ujson.dumps([s.value, o.value]) + '\n').encode('utf-8'))
                except KeyError:
                    logging.error("could not find file {}wiki-20170801-{}.ttl".format(language, abstracts_path_ending))



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_generate_model.log', filemode='w',level=logging.INFO)
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    #writeJsonLines('corpus_abstracts_short.jsonl.gz', 'transitive_redirects_en.ttl.bz2', 'short_abstracts_en.ttl.bz2','short-abstracts')
    #writeJsonLines('corpus_abstracts_long.jsonl.gz', 'transitive_redirects_en.ttl.bz2', 'long_abstracts_en.ttl.bz2', 'long-abstracts')

    #train_model(...)

