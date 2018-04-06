import logging
import boto3
from boto.mturk.question import HTMLQuestion

# does not work but just to save the settings
def submit_mturk():
    client = boto3.client('mturk')

    with open('mTurk_Mapping.html', 'r') as f:
        textfile_temp = f.read()
        html = textfile_temp[textfile_temp.index('<meta content="width=device-width,initial-scale=1"') : textfile_temp.rindex('<!-- CLose internal javascript -->')]
        #html = textfile_temp.split('<!-- HIT template: Survey-v3.0 -->')[1].split('</script><!-- CLose internal javascript -->')[0]

    response = client.create_hit(
        Title='Find similar wikipages in RuneScape, Marvel Comics and Star Trek Wikis',
        Description='Given a wikipage find a wikipage in another similar wiki which describes the same concept. The topics of the wikis are: RuneScape, Marvel Comics and Star Trek',
        Keywords='wiki, matching, runescape, marvel, star trek',
        Reward='0.4',
        MaxAssignments=1,
        AssignmentDurationInSeconds=2400,  # 40 minutes
        LifetimeInSeconds=604800,  # 1 week
        AutoApprovalDelayInSeconds=1800, # 30 minutes

        QualificationRequirements=[
            {# location = US
                'QualificationTypeId': '00000000000000000071',
                'Comparator':  'EqualTo',
                'LocaleValues': [ {'Country': 'US' } ]
            },
            {# PercentAssignmentsApproved > 95 %
                'QualificationTypeId': '000000000000000000L0',
                'Comparator': 'GreaterThan',
                'IntegerValues': [95]
            },
            {  # NumberHITsApproved > 100
                'QualificationTypeId': '00000000000000000040',
                'Comparator': 'GreaterThan',
                'IntegerValues': [100]
            }
        ],
        Question="""<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
  <HTMLContent><![CDATA[
  {}
  ]]>
  </HTMLContent>
  <FrameHeight>800</FrameHeight>
</HTMLQuestion>""".format(html)
    )
    print(response)



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', #filename='b_select_gold_wikis_based_on_content.log', filemode='w', # filemode='a'
                        level=logging.INFO)

    submit_mturk()
