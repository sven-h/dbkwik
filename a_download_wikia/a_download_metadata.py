import requests
import csv
import re
import logging
import multiprocessing
import time

#http://community.wikia.com/api.php?action=query&list=wkdomains&wkactive=1&wkfrom=1&wkto=100
#http://www.wikia.com/api/v1/Wikis/Details?ids=


def guessing_download_url(wiki_url, timeout=5):
    try:
        domain = wiki_url[7:wiki_url.index('.wikia.com')].replace('-', '').replace('.', '')

        current = ("", "", "", "")  # urldump, compression, date, time
        full = ("", "", "", "")  # urldump, compression, date, time

        for dump_type in ['current','full']:
            for compression in ['7z', 'gz', 'bz2']:
                dump_full_url = "http://s3.amazonaws.com/wikia_xml_dumps/{}/{}/{}_pages_{}.xml.{}".format(domain[0], domain[:2], domain, dump_type, compression)
                #print(dump_full_url)
                r = requests.head(dump_full_url, timeout=timeout)
                #print(r)
                if r.status_code == 200:
                    if dump_type == 'current':
                        current = (r.url, compression, "", "")
                    else:
                        full = (r.url, compression, "", "")
                    break
    except Exception as e:#requests.exceptions.ReadTimeout:
        logging.info("can not get guess download page from {} Exception {}".format(wiki_url, str(e)))
        return ("", "", "", ""), ("", "", "", "")
    return current, full

#dump_regex = re.compile("\"(http:.*pages_current.*)\"")
dump_regex = re.compile(
    "<a href=\"(?P<urldump>http://[^<>]+pages_(?P<dumptype>current|full)\.xml\.(?P<compression>[^<>]+))\">(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d\d:\d\d:\d\d)",
    re.IGNORECASE)


def get_download_url_and_time(wiki_url, timeout = 10):
    current = ("", "", "", "")
    full = ("", "", "", "")
    try:
        statistics_html = requests.get(wiki_url + 'wiki/Special:Statistics', timeout=timeout).text
    except Exception as e:#requests.exceptions.ReadTimeout:
        logging.info("can not get statistics page from {}{} - Exception {}".format(wiki_url, 'wiki/Special:Statistics', str(e)))
        return current, full
        #return guessing_download_url(wiki_url)

    for match in dump_regex.finditer(statistics_html):
        if match.group('dumptype').lower() == "current":
            current = (match.group("urldump"), match.group("compression"), match.group("date"), match.group("time"))
        else:
            full = (match.group("urldump"), match.group("compression"), match.group("date"), match.group("time"))
    return current, full


def get_number_of_templates(wiki_url, timeout = 5):
    count = 0
    query_continue = None
    try:
        while True:
            json_response = requests.get(wiki_url + 'api.php', params={'action':'query', 'list':'allpages', 'aplimit':500, 'apnamespace':10, 'format':'json', 'apfrom':query_continue}, timeout=timeout).json()

            count += len(json_response['query']['allpages'])
            if 'query-continue' in json_response:
                query_continue = json_response['query-continue']['allpages']['apfrom']
            else:
                break
        return count
    except Exception as e:#requests.exceptions.ReadTimeout:
        logging.info("can not get amount of templates from {} - Exception {}".format(wiki_url, str(e)))
        return ''


def remove_line_breaks(text):
    if text:
        return text.replace('\r', '').replace('\n', ' ')
    else:
        return ''

def process_one_item(item):
    try:
        wiki_url = item.get('url')

        current, full = get_download_url_and_time(wiki_url)

        #count_of_templates = get_number_of_templates(wiki_url)

        details = [item.get('id'), remove_line_breaks(item.get('title')), wiki_url, item.get('wordmark'),
                   item.get('topUsers'), item.get('headline'), remove_line_breaks(item.get('name')), item.get('domain'),
                   item.get('hub'), item.get('lang'), item.get('topic'), item.get('flags'),
                   remove_line_breaks(item.get('desc')), item.get('image'), item.get('wam_score')]

        stats = item.get('stats')
        statistics = [stats.get('edits', 0), stats.get('articles', 0), stats.get('pages', 0),
                      stats.get('users', 0), stats.get('activeUsers', 0), stats.get('images', 0),
                      stats.get('videos', 0), stats.get('admins', 0), stats.get('discussions', 0)]#, count_of_templates]

        return details + statistics + list(current) + list(full)
    except Exception as e:
        logging.info("can not process one item. {}".format(str(e)))
        return ['']*32


def create_csv():
    pool = multiprocessing.Pool(processes=16)

    with open('wikis.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['id', 'title', 'url', 'wordmark',
                            'topUsers', 'headline', 'name', 'domain',
                            'hub', 'lang', 'topic', 'flags',
                            'desc', 'image', 'wam_score',
                            'stats_edits', 'stats_articles', 'stats_pages',
                            'stats_users', 'stats_activeUsers', 'stats_images',
                            'stats_videos', 'stats_admins', 'stats_discussions',# 'count_templates',
                            'current_dump_url', 'current_compression', 'current_date', 'current_time',
                            'full_dump_url', 'full_compression', 'full_date', 'full_time'])

        offset = 1 # 1 634 061
        windows_size = 100
        while True:
            start_time = time.perf_counter()
            try:
                r = requests.get('http://www.wikia.com/api/v1/Wikis/Details',
                                 params={'ids': ','.join([str(i) for i in range(offset, offset + windows_size)])})
                items = r.json().get('items')
            except Exception as e:
                logging.info("request ids from {} to {} - Exception parse json: {}".format(offset, offset + windows_size,str(e)))
                offset += windows_size
                continue

            if items is None or len(items) == 0:
                if offset > 2000000:  # 2 000 000
                    logging.info("request ids from {} to {} - took {} - break".format(offset, offset + windows_size,time.perf_counter() - start_time))
                    break
                else:
                    logging.info("request ids from {} to {} - took {} - continue".format(offset, offset + windows_size,time.perf_counter() - start_time))
                    offset += windows_size
                    continue

            #if offset > 500:  # len(items) == 0:
            #    break
            try:
                results = pool.imap(process_one_item, items.values()) # threading
                #results = list(map(process_one_item, items.values()))#no threading
            except Exception as e:
                logging.info("request ids from {} to {} - Exception map: {}".format(offset, offset + windows_size,str(e)))
                offset += windows_size
                continue
            csvwriter.writerows(results)

            logging.info("request ids from {} to {} - took {}".format(offset, offset + windows_size, time.perf_counter() - start_time))
            offset += windows_size


def test_dumps():
    with open('../wiki_metadata.csv', newline='', encoding='utf8') as f, open('new_crawl.csv', 'w', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(f)
        csvwriter = csv.writer(csvfile)
        next(reader)
        i = 0
        for row in reader:
            # only wikis with a downloadlink
            if row[24] != "":
                current, full = get_download_url_and_time(row[2])
                csvwriter.writerow(['-' in row[2], row[0], row[1], row[2], row[24]] + list(current) + list(full))
                i += 1
                if i % 10 == 0:
                    logging.info(i)
                    #break


def main():
    #logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='a_download_metadata.log', filemode='w', level=logging.INFO)
    create_csv()
    #test_dumps()

if __name__ == "__main__":
    main()
