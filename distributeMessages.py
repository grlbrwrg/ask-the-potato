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
        records = event["Records"]
        queue = []
        for record in records:
            if 'Sns' in record:
                message = json.loads(record['Sns']['Message'])
                asker_chat_id = message['chat_id']
                question = message['question']
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
    if not 'conversations' in answerer['Item']:
        conversations = [openAnswer]
    else:
        conversations = answerer['Item']['conversations']
    conversations.append(openAnswer)
    
    dynamoUpdate = table.update_item(
    Key={
        'id': int(answerer_chat_id)
    },
    UpdateExpression="set conversations = :c, updated_at = :u",
    ExpressionAttributeValues={
        ':c': conversations,
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
    i = 0
    while i < amount:
        chat_id = queue.pop(0)
        chat_ids.append(chat_id)
        queue.append(chat_id)
        i+=1
    return queue,chat_ids
    

    