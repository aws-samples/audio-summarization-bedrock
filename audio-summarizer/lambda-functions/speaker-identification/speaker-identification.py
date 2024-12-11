# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Speaker Identification Lambda Function

This AWS Lambda function processes transcription job results to identify and format speaker-separated conversations.

Functionality:
1. Receives transcription job results from Amazon Transcribe
2. Extracts speaker labels and transcribed text
3. Processes and formats conversations with speaker identification and timestamps
4. Saves the formatted output to S3

"""

import json
import boto3
import datetime
import codecs
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
        transcription_job = event.get('TranscriptionJob', {})
        transcript = transcription_job.get('Transcript', {})
        transcript_file_uri = transcript.get('TranscriptFileUri', None)
        
        session = boto3.Session()
        region = session.region_name
         
        # Extract the bucket name
        parts = transcript_file_uri.replace("https://s3.{region}.amazonaws.com/", "").split("/")
        print (parts)
    
        # retrieving bucket name and object_key
        bucket_name = parts[3]
        object_key = parts[4]
        
        # Set up S3 client
        s3_client = boto3.client('s3')

        # Retrieve the object
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        
        # Get the object content
        object_content = response['Body'].read().decode('utf-8')
        
        logger.info(f'Object content: {object_content}')

        data =  json.loads(object_content)  
        
        # Extract the necessary data
        labels = data['results']['speaker_labels']['segments']
        speaker_start_times = {}
        for label in labels:
            for item in label['items']:
                speaker_start_times[item['start_time']] = item['speaker_label']
        items = data['results']['items']
    
        # Process the data
        lines = []
        line = ''
        time = 0
        speaker = 'null'
        for item in items:
            content = item['alternatives'][0]['content']
            if item.get('start_time'):
                current_speaker = speaker_start_times[item['start_time']]
            elif item['type'] == 'punctuation':
                line = line + content
            if current_speaker != speaker:
                if speaker:
                    lines.append({'speaker': speaker, 'line': line, 'time': time})
                line = content
                speaker = current_speaker
                time = item['start_time']
            elif item['type'] != 'punctuation':
                line = line + ' ' + content
        lines.append({'speaker': speaker, 'line': line, 'time': time})
        sorted_lines = sorted(lines, key=lambda k: float(k['time']))
    
        # Create the output
        output = []
        for line_data in sorted_lines:
            line = '[' + str(datetime.timedelta(seconds=int(round(float(line_data['time']))))) + '] ' + line_data.get('speaker') + ': ' + line_data.get('line')
            output.append(line)
    
        # Save the output to S3
        s3 = boto3.client('s3')
        output_key = object_key.rsplit('.', 1)[0]
        
        
        object_key = output_key +'-speaker-identification.txt'  # Replace with the desired object key
        output_text = '\n\n'.join(output)
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=output_text.encode('utf-8'))
    
        # Return a success message
        return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Speaker identification completed successfully',
            'bucket_name': bucket_name,
            'object_key': object_key
        })
    }
    
    
    
    
        