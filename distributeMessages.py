import json
import os
import sys
import traceback
import time
here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, "./vendored"))

import requests

import boto3
dynamodb = boto3.resource('dynamodb')

TOKEN = os.environ['TELEGRAM_TOKEN']
BASE_URL = "https://api.telegram.org/bot{}".format(TOKEN)


def main(event, context):
    try:
        print('event:')
        print(event)
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        
        records = event["Records"]
        queue = []
        for record in records:
            # get all questions from the event record
            if 'Sns' in record:
                message = json.loads(record['Sns']['Message'])
                asker_chat_id = message['chat_id']
                question = message['question']
            
            # check if there are any questions that haven't been sent to anybody
            print(asker_chat_id)
            print(question)
            if queue == []:
                queue = getQueueFromDynamo()
            queue,answerer_chat_ids = getChatIdsfromQueue(1,queue)
            for answerer_chat_id in answerer_chat_ids:
                addOpenAnswerToAnswerer(answerer_chat_id,asker_chat_id,question)
                sendTelegramMessage(question,answerer_chat_id)

    except Exception as e:
        print(e)
        traceback.print_exc()

    return {"statusCode": 200}

    
def updateQuestionsOfAsker(asker_chat_id,questions):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    timestamp = int(time.time() * 1000)
    dynamoUpdate = table.update_item(
    Key={
        'id': int(asker_chat_id)
    },
    UpdateExpression="set questions = :q, updated_at = :u",
    ExpressionAttributeValues={
        ':q': questions,
        ':u': timestamp
    },
    ReturnValues="UPDATED_NEW"
    )
    return dynamoUpdate
    
def addOpenAnswerToAnswerer(answerer_chat_id,asker_chat_id,question):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    answerer = table.get_item(Key={'id':int(answerer_chat_id)})
    timestamp = int(time.time() * 1000)
    
    openAnswer = {'asker':int(asker_chat_id),'question':question}
    answers = []
    if not 'answers' in answerer['Item']:
        answers = [openAnswer]
    else:
        answers.append(openAnswer)
    
    dynamoUpdate = table.update_item(
    Key={
        'id': int(answerer_chat_id)
    },
    UpdateExpression="set answers = :a, updated_at = :u",
    ExpressionAttributeValues={
        ':a': answers,
        ':u': timestamp
    },
    ReturnValues="UPDATED_NEW"
    )
    return dynamoUpdate
    
def sendTelegramMessage(text,chat_id):
    payload = {"text": str(text).encode("utf8"), "chat_id": chat_id}
    url = BASE_URL + "/sendMessage"
    r = requests.post(url, payload)
    return r
    
def getQueueFromDynamo():
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    dynamoQueue = table.get_item(Key={'id':0})
    if not 'queue' in dynamoQueue['Item']:
        queue = []
    else:
        queue = dynamoQueue['Item']['queue']
    return queue

def updateQueueOnDynamo(queue):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    dynamoResponse = table.update_item(
    Key={
        'id': 0
    },
    UpdateExpression="set queue = :q",
    ExpressionAttributeValues={
        ':q': queue
    },
    ReturnValues="UPDATED_NEW"
    )
    return dynamoResponse
    
def getChatIdsfromQueue(amount,queue):
    chat_ids = []
    for i in range(amount):
        chat_id = queue.pop(0)
        chat_ids.append(chat_id)
        queue.append(chat_id)
    return queue,chat_ids
    

    