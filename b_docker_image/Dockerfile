FROM openjdk:8-jdk-alpine

RUN adduser -S extractor && \
    mkdir /home/extractor/base && \
    mkdir /home/extractor/log && \
    apk add --no-cache maven python py-pip bash p7zip && \
    pip install --upgrade awscli && \
    apk -v --purge del py-pip && \
    cd /home/extractor/ && \
    wget https://github.com/sven-h/extraction-framework/archive/v1.4.tar.gz -O download.tar.gz && \
    mkdir extraction-framework && \
    tar -xzf download.tar.gz -C extraction-framework --strip-components 1 && \
    rm /home/extractor/download.tar.gz && \
    cd /home/extractor/extraction-framework && \
    mvn install -pl core,dump,scripts -am

COPY start_aws.sh /home/extractor/start.sh

CMD ["/bin/bash", "/home/extractor/start.sh", ">", "/home/extractor/script.log", "2>&1"]
