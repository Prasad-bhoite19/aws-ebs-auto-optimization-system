import boto3
import datetime

ec2 = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

TABLE_NAME = "EBSVolumeConversionLog"

SNS_TOPIC_ARN = "arn:aws:sns:eu-north-1: (Account_ID) :ebs-conversion-alert"

table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):

    print("Scanning for gp2 volumes with AutoConvert=true tag")

    volumes = ec2.describe_volumes(
        Filters=[
            {'Name': 'volume-type', 'Values': ['gp2']},
            {'Name': 'tag:AutoConvert', 'Values': ['true']}
        ]
    )

    print("Volumes found:", volumes)

    for volume in volumes['Volumes']:

        volume_id = volume['VolumeId']
        size = volume['Size']
        old_type = volume['VolumeType']
        region = ec2.meta.region_name
        timestamp = str(datetime.datetime.utcnow())

        instance_id = "N/A"

        if volume['Attachments']:
            instance_id = volume['Attachments'][0]['InstanceId']

        try:

            ec2.modify_volume(
                VolumeId=volume_id,
                VolumeType='gp3'
            )

            status = "SUCCESS"

        except Exception as e:

            status = "FAILED"
            print(str(e))

        table.put_item(
            Item={
                'VolumeId': volume_id,
                'Timestamp': timestamp,
                'InstanceId': instance_id,
                'OldType': old_type,
                'NewType': 'gp3',
                'Region': region,
                'Size': size,
                'Status': status
            }
        )

        message = f"""
EBS Volume Converted

Volume ID: {volume_id}
Instance ID: {instance_id}
Old Type: {old_type}
New Type: gp3
Size: {size} GB
Region: {region}
Status: {status}
"""

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="EBS Volume Converted",
            Message=message
        )

    return {
        "statusCode": 200,
        "body": "Volume optimization completed"
    }
