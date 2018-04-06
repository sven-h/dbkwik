import boto3
import csv
import time
#http://boto3.readthedocs.io/en/latest/index.html
#http://boto3.readthedocs.io/en/latest/reference/services/batch.html


def create_compute_environment(client):
    response = client.create_compute_environment(
        computeEnvironmentName='ComputeEnvDbkwik',
        type='MANAGED',
        state='ENABLED',
        computeResources={
            'type': 'SPOT',
            'minvCpus': 0,
            'desiredvCpus': 0,
            'maxvCpus': 500, # when 10 then 5 c3.large are spawned because each one has 2 cpus
            'instanceTypes': [
                'c3.large',
            ],
            'subnets': [ 
                'subnet-b0b1c98f', # us-east-1a
                'subnet-b586f69a' # us-east-1e
            ],
            'securityGroupIds': ['security_groupid'],
            'ec2KeyPair': 'sven', #'test',
            'instanceRole': 'ecsInstanceRole', #'ecsInstanceRole',
            'bidPercentage': 40, # actually 30-40
            'spotIamFleetRole': 'AmazonEC2SpotFleetTaggingRole' 
        },
        serviceRole='service_role' 
    )
    print(response)

def create_job_queue(client):
    response = client.create_job_queue(
        jobQueueName='Queue_ComputeEnvDbkwik',
        state='ENABLED',
        priority=1,
        computeEnvironmentOrder=[
            {
                'order': 1,
                'computeEnvironment': 'ComputeEnvDbkwik'
            },
        ]
    )
    print(response)


def register_job_definition(client):
    response = client.register_job_definition(
        jobDefinitionName='Dbkwik_job',
        type='container',
        containerProperties={
            'image': '310304493222.dkr.ecr.us-east-1.amazonaws.com/dbkwik:latest',
            'vcpus': 2,
            'memory': 3500, # The hard limit (in MiB)
            'jobRoleArn': 'AmazonS3FullAccess',
        },
        retryStrategy={ 'attempts': 1 }
    )
    print(response)


def submit_job(client, s3_url, language, subdomain, file_name, job_id):
    response = client.submit_job(
        jobName="Dbkwik_job_"+str(job_id),
        jobQueue='Queue_ComputeEnvDbkwikNew',
        #arrayProperties={'size': 1 },
        #dependsOn=[{'jobId': 'string', 'type': 'N_TO_N' | 'SEQUENTIAL' }, ],
        jobDefinition='Dbkwik_job:1',#'Dbkwik_job:4',
        #parameters={'string': 'string'},
        containerOverrides={
            #'vcpus': 1,
            #'memory': 123,
            #'command': [ 'string', ],
            'environment': [
                {'name': 'DBKWIK_S3_URL',    'value': s3_url },
                {'name': 'DBKWIK_LANGUAGE',  'value': language},
                {'name': 'DBKWIK_SUBDOMAIN', 'value': subdomain},
                {'name': 'DBKWIK_FILE_NAME', 'value': file_name}
            ]
        }
        #retryStrategy={'attempts': 1}
    )
    print(response)


def submit_dbkwik_jobs(client):
    with open('wikis.csv', newline='', encoding='utf-8') as infile:
        csvreader = csv.reader(infile)
        next(csvreader)#do not use header
        i = 0
        for row in csvreader:
            current_dump_url = row[24]
            if not current_dump_url:
                continue
            i += 1
            language = row[9]
            if not language:
                language = 'en'

            wiki_url = row[2]
            http_index = wiki_url.index('http://')
            wikia_index = wiki_url.index('.wikia.com')
            subdomain = wiki_url[http_index + 7:wikia_index]

            file_name = row[0] + "~" + language + "~" + subdomain + "~" + subdomain + ".wikia.com"

            print("execute job number {}: DBKWIK_S3_URL = '{}' DBKWIK_LANGUAGE = '{}' DBKWIK_SUBDOMAIN = '{}' DBKWIK_FILE_NAME = '{}'".format(i,current_dump_url, language, subdomain, file_name ))
            submit_job(client, current_dump_url, language, subdomain, file_name, i)
            #if i > 20:
            #    break

def delete_compute_environment(client, name):
    response = client.update_compute_environment(
        computeEnvironment=name,
        state='DISABLED',
    )
    print(response)
    time.sleep(5)#TODO: wait until status
    response = client.delete_compute_environment(
        computeEnvironment=name
    )
    print(response)

def delete_job_queue(client, name):
    response = client.update_job_queue(
        jobQueue=name,
        state='DISABLED'
    )
    print(response)
    time.sleep(5)#TODO: wait until status
    response = client.delete_job_queue(
        jobQueue=name
    )
    print(response)

def delete_job_definition(client):
    response = client.deregister_job_definition(
        jobDefinition='Dbkwik_job' # add revision  Dbkwik_job:2
    )
    print(response)

def kill_all_jobs(client):
    nextToken = ''
    while True:
        response = client.list_jobs(
            jobQueue='Queue_ComputeEnvDbkwik_Live',
            jobStatus='RUNNABLE',
            maxResults=100,
            nextToken = nextToken
        )

        if 'nextToken' in response:
            nextToken = response['nextToken']
        else:
            break

        for job in response['jobSummaryList']:
            print(job['jobId'])
            client.cancel_job(
                jobId = job['jobId'],
                reason = "Job stopped by user"
            )

        print(response['jobSummaryList'])
    print("finish")
    #print(response)

def main():
    # check that outbound vpc (firewall allows http and https to anywhere)
    #session = boto3.Session(profile_name='default')
    #client = session.client('batch')
    client = boto3.client('batch')
    create_compute_environment(client)
    create_job_queue(client)
    register_job_definition(client)
    submit_dbkwik_jobs(client)
    #kill_all_jobs(client)

if __name__ == "__main__":
    main()