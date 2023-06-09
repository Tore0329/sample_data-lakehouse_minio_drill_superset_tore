from typing import List
import os
#import airflow
from airflow.decorators import dag, task
import requests
#import time
from datetime import datetime, timedelta
from operator import itemgetter
#import csv
import json
import pendulum
import pandas as pd
from minio import Minio
from io import BytesIO
import os
import json

##-- Global vars

default_task_args = {
    'retries' : 10,
    'retry_delay' : timedelta(minutes=1),
    'retry_exponential_backoff' : True,
}

##-- Methodsx       

def setups():
    global URL, PATH
    URL = 'https://sa-mp.im/api/v1/players/get' 
    PATH = './dags/ProjektDataService/data'

@dag(
    dag_id='online_players',
    schedule=timedelta(minutes=2),
    start_date=pendulum.now("Europe/Copenhagen").subtract(days=1),
    catchup=False,
    max_active_tasks=5,
    max_active_runs=5,
    tags=['experimental', 'samp', 'rest api'],
    default_args=default_task_args,)
def online_players():
    if __name__ != "__main__":
        print("##-- Calling API")
        setups()
        eProdex_jsons = extract_PlayerProdex()
        write_to_bucket(eProdex_jsons, 'live')

@task
def extract_PlayerProdex(**kwargs):
    global URL, PATH
    ts = datetime.fromisoformat(kwargs['ts'])

    return pull_data('PlayerProdex', ts)

@task
def write_to_bucket(eProdex_json, table_path):
    #MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME')
    bucket = 'prodex'
    MINIO_ACCESS_KEY = os.getenv('MINIO_ROOT_USER')
    MINIO_SECRET_KEY = os.getenv('MINIO_ROOT_PASSWORD')
    client = Minio("minio:9000", access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    found = client.bucket_exists(bucket)

    if not found:
        client.make_bucket(bucket)
    
    with open(eProdex_json, 'r') as jf:
        prodex_json = json.load(jf)

    df = pd.DataFrame(prodex_json)
    file_data = df.to_parquet(index=False)
    prodex_filename = eProdex_json.split('/')[-1]
    filename = (
        f"{table_path}/{prodex_filename}.parquet"
    )
    client.put_object(
        bucket, filename, data=BytesIO(file_data), length=len(file_data), content_type="application/csv"
    )
    os.remove(eProdex_json)

def pull_data(data_name: str, data_timedate: datetime) -> str:
    r = requests.get(URL)

    if r.status_code != requests.codes.ok:
        raise Exception('http not 200 ok', r.text)

    rjson = r.json()

    for x in rjson:
        x['ts'] = f"{data_timedate.year}-{data_timedate.month}-{data_timedate.day} {data_timedate.hour}:{data_timedate.minute}:{data_timedate.second}"

    time_stamp = data_timedate.isoformat(timespec='seconds').replace(':', '.')
    fName = f'{PATH}/{data_name}_{time_stamp}.json'

    with open(fName, "w+") as f:
        f.write(json.dumps(rjson))
        
    return fName

online_players()