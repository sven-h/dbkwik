# DBkWik: A Consolidated Knowledge Graph from thousands of Wikis

This repository contains all the code and gold standards for creating the DBkWik dataset.

## Abstract
While popular knowledge graphs such as DBpedia and YAGO are built from Wikipedia, Wikifarms like Fandom contain Wikis for specific topics, which are often complementary to the information contained in Wikipedia, and thus DBpedia and YAGO. Extracting these Wikis with the DBpedia extraction framework is possible, but results in many isolated knowledge graphs. In this paper, we show how to create one consolidated knowledge graph, called DBkWik, from thousands of Wikis. We perform entity resolution and schema matching, and show that the
resulting large-scale knowledge graph is complementary to DBpedia.

## Links

- to the gold standards (in alignment format - see [alignment api](http://alignapi.gforge.inria.fr/format.html):
  - [DBkWik to Dbpedia](https://github.com/sven-h/dbkwik/tree/master/f_gold_mapping_dbpedia/gold)
  - [DBkWik interwiki](https://github.com/sven-h/dbkwik/tree/master/e_gold_mapping_interwiki/gold)
  - [to the corresponding unprocessed dumps](http://data.dws.informatik.uni-mannheim.de/dbkwik/KGs_for_gold_standard.tar.gz)
- to a csv file with all wikis available in Wikia/Fandom: [Link](http://data.dws.informatik.uni-mannheim.de/dbkwik/2018-03-fandom_statistics.csv)
- to the unprocessed wiki dumps: [Link](http://data.dws.informatik.uni-mannheim.de/dbkwik/dbkwik-v1.0.tar.gz)
- to the processed dump: [Link](http://data.dws.informatik.uni-mannheim.de/dbkwik/dbkwik_fusion-v1.0.tar.gz)
