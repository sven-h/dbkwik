#!/bin/bash
LC_ALL=C
source_folder="smash_doc2vec"
target_folder="smash_doc2vec_sorted"

for filename in $source_folder/*.ttl $source_folder/*.txt; do
    #possible: -T dir  --parallel=N
    file_base=$(basename "$filename")
    if [ $file_base != 'anchor-text.ttl' ] 
    then
        echo $file_base
        sort -u -S 90% -T /notexistent/ -o $target_folder/"$file_base" $source_folder/"$file_base"
    fi
done