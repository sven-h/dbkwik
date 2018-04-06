import logging
import csv
from itertools import chain
from os import path
import re
import gzip
import random

def get_titles_from_dump_fast(file_handle):
    #title_finder = re.compile(r"<title>(.*?)</title>[ \n]*?<ns>0</ns>")
    title = []
    title_finder = re.compile(r"<title>(.*?)</title>")
    #with open(509_en_harrypotter_pages_current.xml', 'r', encoding='utf8') as f:
    for line in file_handle: # f:
        m = title_finder.search(line)
        if m is not None:
            #print(m.group(1))
            if "<ns>0</ns>" in next(file_handle):
                title.append(m.group(1))
    return title

def replace_csv_in_template(template_path, data, out):
    with open(template_path, 'r') as template_file:
        template = template_file.read()
    with open(data) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            for name in reader.fieldnames:
                template = template.replace("${" + name + "}", row[name])
                print("replace {} with {}".format("${" + name + "}", row[name]))
            break  # only first line to test
    with open(out, "w") as out:
        out.write(template)


def create_template():
    for i in range(0, 10):
        print(
"""<li>
    <a target="_blank" href="${domain_a}/wiki/${wiki_~}">${domain_a}/wiki/${wiki_~}</a> with title &quot;${raw_~}&quot;
    <div class="input-group">
      <input type="text" class="form-control" name="~_mapping" value="${domain_b}/wiki/..." required pattern="${domain_b}/wiki/[^.].*">
      <span class="input-group-addon"><label><input class="matching_article" type="checkbox" value=""> No matching article</label></span>
    </div> 
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_b}/wiki/Special:AllPages">list all pages</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_b}/wiki/Special:Search?query=${encoded_~}">search with wiki</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="http://www.google.com/search?q=site:${domain_b}+${encoded_~}">search with Google</a>
</li>
</br>
""".replace("~", str(i)))

#"""<li>
#    <a target="_blank" href="${domain_a}/wiki/${wiki_~}">${domain_a}/wiki/${wiki_~}</a> with title "${raw_~}
#    <input type="url" class="form-control" name="~_mapping" placeholder="Wiki URL or 'not:possible'" required>
#    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_b}/wiki/Special:Search?query=${encoded_~}">search with wiki</a>
#    <a class="btn btn-primary btn-sm" target="_blank" href="http://www.google.com/search?q=site:${domain_b}+${encoded_~}">search with Google</a>
#    <a class="btn btn-primary btn-sm" target="_blank" href="http://www.bing.com/search/search?q=site:${domain_b}+${encoded_~}">search with Bing</a>
#    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_b}/wiki/Special:AllPages">list all pages</a>
#</li>
#</br>
#""".replace("~", str(i)))


def write_m_turk_csv(mturk_csv_file, dump_paths):

    links_per_hit = 10
    with open(mturk_csv_file, "w", newline='') as out:
        writer = csv.writer(out)
        # wiki one id, wiki two id, title one , title two,
        writer.writerow(['id_a','id_b', 'title_a', 'title_b', 'domain_a', 'domain_b', *chain.from_iterable(("raw_" + str(i), "wiki_" + str(i), "encoded_" + str(i)) for i in range(0, links_per_hit))])

        for wiki_one_path, wiki_one_title, wiki_two_path, wiki_two_title in dump_paths:
            wiki_one_parts = path.basename(wiki_one_path).split('~')
            wiki_two_parts = path.basename(wiki_two_path).split('~')

            wiki_one_id = wiki_one_parts[0]
            wiki_two_id = wiki_two_parts[0]

            wiki_one_domain = wiki_one_parts[2]
            wiki_two_domain = wiki_two_parts[2]

            with gzip.open(wiki_one_path, 'rt', encoding='utf8') as f:
                titles_one = get_titles_from_dump_fast(f)


            for i in range(3):
                row = [wiki_one_id, wiki_two_id, wiki_one_title, wiki_two_title, "http://" + wiki_one_domain + ".wikia.com", "http://" + wiki_two_domain + ".wikia.com"]
                for title in random.sample(titles_one,links_per_hit):
                    row.append(title) # raw
                    row.append(title.replace(' ', '_'))  # wiki
                    row.append(title.replace(' ', '+')) # encoded
                writer.writerow(row)





if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='b_select_gold_wikis_based_on_content.log', filemode='w', # filemode='a'
                        level=logging.INFO)

    #create_template()

    write_m_turk_csv('mturk_input.csv', [
        ('304~en~runescape~runescape.wikia.com.gz', 'The RuneScape Wiki',
         '691244~en~oldschoolrunescape~oldschoolrunescape.wikia.com.gz', 'Old School RuneScape Wiki',
         '1267847~en~darkscape~darkscape.wikia.com.gz', 'DarkScape Wikia')
    ])
    replace_csv_in_template('mTurk_Mapping.html', 'mturk_input.csv', 'mTurk_Mapping_example.html')