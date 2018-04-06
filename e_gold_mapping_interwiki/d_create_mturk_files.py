import logging
import csv
from itertools import chain
from os import path
import re
import gzip
import random
import requests

def get_titles_from_dump_fast(file_handle):
    #title_finder = re.compile(r"<title>(.*?)</title>[ \n]*?<ns>0</ns>")
    title = []
    title_finder = re.compile(r"<title>(.*?)</title>")
    #with open('C:\\dev\\dbkwik_extraction\\dbkwik_own\\dumps\\transformed\\509_en_harrypotter_pages_current.xml', 'r', encoding='utf8') as f:
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
"""<li style="margin-bottom:40px;">
    <p><a target="_blank" href="${domain_src}/wiki/${wiki_~}">${domain_src}/wiki/${wiki_~}</a> with title &quot;${raw_~}&quot; </p>
    Find it in <a target="_blank" href="${domain_dst1}">${title_dst1}</a>:
    <div class="input-group">
      <input type="text" class="form-control" name="~_mapping_dst1" value="${domain_dst1}/wiki/..." required pattern="${domain_dst1}/wiki/[^.].*">
      <span class="input-group-addon"><label><input class="matching_article" type="checkbox" value=""> No matching article</label></span>
    </div>
    <p>
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_dst1}/wiki/Special:AllPages">list all pages</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_dst1}/wiki/Special:Search?query=${encoded_~}">search with wiki</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="http://www.google.com/search?q=site:${domain_dst1}+${encoded_~}">search with Google</a>
    </p>
    
    Find it in <a target="_blank" href="${domain_dst2}">${title_dst2}</a>:
    <div class="input-group">
      <input type="text" class="form-control" name="~_mapping_dst2" value="${domain_dst2}/wiki/..." required pattern="${domain_dst2}/wiki/[^.].*">
      <span class="input-group-addon"><label><input class="matching_article" type="checkbox" value=""> No matching article</label></span>
    </div>
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_dst2}/wiki/Special:AllPages">list all pages</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="${domain_dst2}/wiki/Special:Search?query=${encoded_~}">search with wiki</a>
    <a class="btn btn-primary btn-sm" target="_blank" href="http://www.google.com/search?q=site:${domain_dst2}+${encoded_~}">search with Google</a>
</li>
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


def get_random_sample_list(wiki_titles, wiki_url, links_per_hit, hit_count):
    samples = set()
    while len(samples) < links_per_hit * hit_count:
        possible_title = random.choice(wiki_titles)
        if 'disambiguation' in possible_title:
            print("dis: " + possible_title)
            continue
        #check redirects
        r = requests.get(wiki_url + '/api.php', params={'action': 'query', 'titles': possible_title,'format':'json', 'redirects':''})
        if 'redirects' in r.json()['query']:
            redirect_list = r.json()['query']['redirects']
            if len(redirect_list) > 0:
                possible_title = redirect_list[0]['to']
        samples.add(possible_title)

    sample_list = list(samples)

    ret_list = []
    for i in range(hit_count):
        ret_list.append(sample_list[:links_per_hit])
        del sample_list[:links_per_hit]

    return ret_list



def write_m_turk_csv(mturk_csv_file, dump_paths, links_per_hit = 10, hit_count = 3):
    with open(mturk_csv_file, "w", newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        # wiki one id, wiki two id, title one , title two,
        writer.writerow([
            'id_src', 'title_src', 'domain_src',
            'id_dst1', 'title_dst1', 'domain_dst1',
            'id_dst2', 'title_dst2', 'domain_dst2',
            *chain.from_iterable(("raw_" + str(i), "wiki_" + str(i), "encoded_" + str(i)) for i in range(0, links_per_hit))])

        for wiki_one_path, wiki_one_title, wiki_one_id, wiki_one_url, \
            wiki_two_path, wiki_two_title, wiki_two_id, wiki_two_url, \
            wiki_three_path, wiki_three_title, wiki_three_id, wiki_three_url in dump_paths:

            with gzip.open(wiki_one_path, 'rt', encoding='utf8') as f:
                titles_one = get_titles_from_dump_fast(f)
            with gzip.open(wiki_two_path, 'rt', encoding='utf8') as f:
                titles_two = get_titles_from_dump_fast(f)
            with gzip.open(wiki_three_path, 'rt', encoding='utf8') as f:
                titles_three = get_titles_from_dump_fast(f)


            #using first as source
            for samples in get_random_sample_list(titles_one, wiki_one_url, links_per_hit, hit_count):
                row = [ wiki_one_id, wiki_one_title, wiki_one_url,
                        wiki_two_id, wiki_two_title, wiki_two_url,
                        wiki_three_id, wiki_three_title, wiki_three_url]
                for title in samples:
                    row.append(title) # raw
                    row.append(title.replace(' ', '_')) # wiki
                    row.append(title.replace(' ', '+')) # encoded
                writer.writerow(row)

            # using second as source
            for samples in get_random_sample_list(titles_two, wiki_two_url, links_per_hit, hit_count):
                row = [ wiki_two_id, wiki_two_title, wiki_two_url,
                        wiki_one_id, wiki_one_title, wiki_one_url,
                        wiki_three_id, wiki_three_title, wiki_three_url]
                for title in samples:
                    row.append(title) # raw
                    row.append(title.replace(' ', '_')) # wiki
                    row.append(title.replace(' ', '+')) # encoded
                writer.writerow(row)

            # using third as source
            for samples in get_random_sample_list(titles_three, wiki_three_url, links_per_hit, hit_count):
                row = [wiki_three_id, wiki_three_title, wiki_three_url,
                       wiki_one_id, wiki_one_title, wiki_one_url,
                       wiki_two_id, wiki_two_title, wiki_two_url]
                for title in samples:
                    row.append(title)  # raw
                    row.append(title.replace(' ', '_'))  # wiki
                    row.append(title.replace(' ', '+'))  # encoded
                writer.writerow(row)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='b_select_gold_wikis_based_on_content.log', filemode='w', # filemode='a'
                        level=logging.INFO)

    #create_template()

    base = 'dump/'
    write_m_turk_csv('mturk_input.csv', [
        ( base + '304~en~runescape~runescape.wikia.com.gz', 'RuneScape Wiki', 304, 'http://runescape.wikia.com',
          base + '691244~en~oldschoolrunescape~oldschoolrunescape.wikia.com.gz', 'Old School RuneScape Wiki', 691244, 'http://oldschoolrunescape.wikia.com',
          base + '1267847~en~darkscape~darkscape.wikia.com.gz', 'DarkScape Wiki', 1267847, 'http://darkscape.wikia.com'),

        (base + '2233~en~marvel~marvel.wikia.com.gz', 'Marvel Database', 2233,'http://marvel.wikia.com',
         base + '330278~en~heykidscomics~heykidscomics.wikia.com.gz', 'Hey Kids Comics Wiki', 330278, 'http://heykidscomics.wikia.com',
         base + '2237~en~dc~dc.wikia.com.gz', 'DC Database', 2237, 'http://dc.wikia.com'),

        (base + '113~en~memory-alpha~memory-alpha.wikia.com.gz', 'Memory Alpha', 113,'http://memory-alpha.wikia.com',
         base + '745~en~stexpanded~stexpanded.wikia.com.gz','Star Trek Expanded Universe', 745, 'http://stexpanded.wikia.com',
         base + '323~en~memory-beta~memory-beta.wikia.com.gz', 'Memory Beta, non-canon Star Trek Wiki', 323, 'http://memory-beta.wikia.com'),
    ])

    #replace_csv_in_template('mTurk_Mapping.html', 'mturk_input.csv', 'mTurk_Mapping_example.html')
