import csv
import urllib.request
import logging
import os


def main():
    if not os.path.exists('dump/'):
        os.makedirs('dump/')

    with open('2018_02_27_wikis_head.csv', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        next(csvreader)
        
        j = 0
        for i, row in enumerate(csvreader):
            current_url = row[24]
            if current_url:
                # id~language~subdomain~domain.compression
                language = row[9]
                if not language:
                    language = 'en'
                
                wiki_url = row[2]
                http_index  = wiki_url.index('http://')
                wikia_index  = wiki_url.index('.wikia.com')
                subdomain = wiki_url[http_index+7:wikia_index]
                
                #url_last_part = current_url[current_url.rindex('/') + 1:]
                file_extension = current_url[current_url.rindex('.') + 1:]
                dest = 'dump/' + row[0] + "~" + language + "~" + subdomain + "~" + subdomain + ".wikia.com." + file_extension
                logging.info("{} - Download {} to {}".format(i, current_url, dest))
                try:
                    #pass
                    urllib.request.urlretrieve(current_url, dest)
                except Exception as e:
                    logging.error("Fail download {} to {}: {}".format(current_url, dest, str(e)))
                    continue
        print(j)
        
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', filename='download.log', filemode='w', level=logging.INFO)
    main()
