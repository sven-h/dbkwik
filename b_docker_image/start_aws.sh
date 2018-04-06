#!/bin/bash

#need following env variables:
#DBKWIK_S3_URL      http://s3.amazonaws.com/wikia_xml_dumps/p/pn/pnw_pages_full.xml.7z
#DBKWIK_LANGUAGE    en
#DBKWIK_SUBDOMAIN   pnw
#DBKWIK_FILE_NAME   123~pnw~pnw.wiki.com.extracted

DBKWIK_S3_URL_EXTENSION="${DBKWIK_S3_URL##*.}"

echo ${DBKWIK_S3_URL}
echo ${DBKWIK_S3_URL_EXTENSION}

#aws s3 cp "${DBKWIK_S3_URL}" /home/extractor/dump_file
wget -O /home/extractor/dump_file "${DBKWIK_S3_URL}"

mkdir -p /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/
touch /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-download-complete

case ${DBKWIK_S3_URL_EXTENSION} in
    bz2) bzip2 -dc /home/extractor/dump_file > /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-pages-articles.xml ;;
    gz)  gunzip -c /home/extractor/dump_file > /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-pages-articles.xml ;;
    7z)  7zr e -so /home/extractor/dump_file > /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-pages-articles.xml ;;
esac

if [ $? -ne 0 ]; then
    echo "Fail uncompressing..."
    exit 1
fi

cd /home/extractor/extraction-framework/dump/
../run extraction extraction.dbkwik.properties ${DBKWIK_SUBDOMAIN}

if [ $? -ne 0 ]; then
    echo "Fail extracting..."
    exit 1
fi

cd /home/extractor/extraction-framework/scripts/
#Create transitive redirects

if [ -f "/home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-redirects.ttl" ]; then

    ../run ResolveTransitiveLinks /home/extractor/base/ redirects transitive-redirects .ttl @downloaded
    if [ $? -ne 0 ]; then
        echo "Fail ResolveTransitiveLinks..."
        exit 1
    fi
    
    if [ -f "/home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801/${DBKWIK_LANGUAGE}wiki-20170801-transitive-redirects.ttl" ]; then    
        #map transitive redirects
        ../run MapObjectUris /home/extractor/base/ transitive-redirects .ttl disambiguations,infobox-properties,topical-concepts -redirected .ttl @downloaded
        if [ $? -ne 0 ]; then
            echo "Fail MapObjectUris..."
            exit 1
        fi
    fi
fi

../run CreateDomainRangeAndTypes @downloaded
if [ $? -ne 0 ]; then
    echo "Fail CreateDomainRangeAndTypes..."
fi
../run RelationExtraction @downloaded
if [ $? -ne 0 ]; then
    echo "Fail RelationExtraction..."
fi


cd /home/extractor/base/${DBKWIK_LANGUAGE}wiki/20170801

tar -czf ${DBKWIK_FILE_NAME}.tar.gz  *.ttl /home/extractor/script.log

aws s3 cp ${DBKWIK_FILE_NAME}.tar.gz s3://dbkwik-uni
