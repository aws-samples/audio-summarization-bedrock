# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import uuid

def lambda_handler(event, context):
    # Create Boto3 clients
    s3 = boto3.client('s3')
    bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    
    # Extract bucket name and object key from the input event
    input_body = event.get("body", "")
    if input_body:
        input_data = json.loads(input_body)
        bucket_name = input_data.get("bucket_name")
        object_key = input_data.get("object_key")
    else:
        print("Invalid input format. Expected JSON with 'bucket_name' and 'object_key' keys.")
        return
    
    # Download the object from S3
    file_obj = s3.get_object(Bucket=bucket_name, Key=object_key)
    content = file_obj['Body'].read().decode('utf-8')

    # Construct the prompt
    prompt = f"{content}\n\nGive me the summary, speakers, key discussions, and action items with owners"

    # Construct the request payload
    body = json.dumps({
        "max_tokens": 4096,
        "temperature": 0.5,
        "messages": [{"role": "user", "content": prompt}],
        "anthropic_version": "bedrock-2023-05-31"
    })
    
    # Invoke the model
    #modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
    modelId = "anthropic.claude-3-5-sonnet-20240620-v1:0" 

    response = bedrock.invoke_model(body=body, modelId=modelId)
    

    # Parse the response
    response_body = json.loads(response.get("body").read())
    content = response_body.get("content")
    summary = content[0]['text']
    
    filename = str(uuid.uuid4())
    object_key = "Bedrock-Sonnet-GenAI-summary-" + filename + ".txt"
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=summary.encode('utf-8'))
    
    
    # Return a success message
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Summary and key discussions generated successfully',
        })
    }