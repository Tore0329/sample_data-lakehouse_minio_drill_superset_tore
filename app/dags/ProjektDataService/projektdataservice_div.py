from typing import List
import os
import airflow
from airflow.decorators import dag, task
import requests
import time
from datetime import datetime, timedelta
from operator import itemgetter
import csv
import json
import pendulum
import pandas as pd
from minio import Minio
from io import BytesIO
import os
import json

##-- Global vars

global URL, data_dir, page_size
URL = 'https://sa-mp.im/api/v1/players/get'
data_dir = './dags/ProjektDataService/data'
page_size = 1000
default_task_args = {
    'retries' : 10,
    'retry_delay' : timedelta(minutes=1),
    'retry_exponential_backoff' : True,
}

##-- Methods

@task
def extract_PlayerProdex(**kwargs):    
    params = {}
    ts = datetime.fromisoformat(kwargs['ts'])
    params['start'] = (ts - timedelta(minutes=9)).replace(tzinfo=None).isoformat(timespec='minutes')
    params['end']   = ts.replace(tzinfo=None).isoformat(timespec='minutes')

    return pull_data('PlayerProdex', ts, params)

@dag( 
    dag_id='online_players',
    schedule=timedelta(minutes=5),
    start_date=pendulum.datetime(2023, 6, 1, 0, 0, 0, tz="Europe/Copenhagen"),
    catchup=True,
    max_active_tasks=5,
    max_active_runs=5,
    tags=['experimental', 'samp', 'rest api'],
    default_args=default_task_args,)
def online_players():
    print("##-- Calling API")
    if __name__ != "__main__":
        eProdex_jsons = extract_PlayerProdex()
        write_to_bucket(eProdex_jsons, 'live')

def pull_data(data_name: str, data_timedate: datetime, params: dict) -> List[str]:
    page_index = 0
    fNames = []
    
    while True:
        if not 'limit' in params.keys():
            params['limit'] = page_size
        params['offset'] = page_index * page_size
        
        r = requests.get(URL, params=params)

        if r.status_code != requests.codes.ok:
            raise Exception('http not 200 ok', r.text)
        else:
            rjson = r.json()
        
        if len(rjson) > 0:
            page_index += 1
            time_stamp = data_timedate.isoformat(timespec='seconds').replace(':', '.')
            fName = f'{data_dir}/{data_name}_{time_stamp}_#{page_index}.json'
            with open(fName, "w+") as f:
                f.write(r.text)
            fNames.append(fName)
        else:
            break
        time.sleep(1)
    return fNames

@task
def write_to_bucket(eProdex_jsons, table_path):
    MINIO_BUCKET_NAME = 'prodex-data'
    MINIO_ACCESS_KEY = os.getenv('MINIO_ROOT_USER')
    MINIO_SECRET_KEY = os.getenv('MINIO_ROOT_PASSWORD')
    client = Minio("minio:9000", access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    found = client.bucket_exists(MINIO_BUCKET_NAME)

    if not found:
        client.make_bucket(MINIO_BUCKET_NAME)
    
    for prodex_json_filepath in eProdex_jsons:
        with open(prodex_json_filepath, 'r') as jf:
            prodex_json = json.load(jf)
        df = pd.DataFrame(prodex_json['records'])
        file_data = df.to_parquet(index=False)
        prodex_filename = prodex_json_filepath.split('/')[-1]
        filename = (
            f"{table_path}/{prodex_filename}.parquet"
        )
        client.put_object(
            MINIO_BUCKET_NAME, filename, data=BytesIO(file_data), length=len(file_data), content_type="application/csv"
        )
        #os.remove(prodex_json_filepath)
##-- Opg 1

url = "https://sa-mp.im/api/v1/players/get"
resp = requests.get(url)
print(f"Count: {len(resp.json())} ->\n{json.dumps(resp.json(), indent=4)}")

##-- Opg 2

online_players()