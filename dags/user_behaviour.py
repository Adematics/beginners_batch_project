import json
from datetime import datetime, timedelta

from utils import _local_to_s3, run_redshift_external_query

from airflow import DAG
from airflow.contrib.operators.emr_add_steps_operator import (
    EmrAddStepsOperator,
)
from airflow.contrib.sensors.emr_step_sensor import EmrStepSensor
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python import PythonOperator

# Config
BUCKET_NAME = Variable.get("BUCKET")
EMR_ID = Variable.get("EMR_ID")
EMR_STEPS = {}
with open("./dags/scripts/emr/clean_loan_tracker.json") as json_file:
    EMR_STEPS = json.load(json_file)

# DAG definition
default_args = {
    "owner": "airflow",
    "depends_on_past": True,
    "wait_for_downstream": True,
    "start_date": datetime(2021, 5, 23),
    "email": ["airflow@airflow.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "user_behaviour",
    default_args=default_args,
    schedule_interval="0 0 * * *",
    max_active_runs=1,
)

loan_tracker_to_raw_data_lake = PythonOperator(
    dag=dag,
    task_id="loan_tracker_to_raw_data_lake",
    python_callable=_local_to_s3,
    op_kwargs={
        "file_name": "./dags/data/loan.csv",
        "key": "raw/loan_tracker/{{ ds }}/loan.csv",
        "bucket_name": BUCKET_NAME,
    },
)


spark_script_to_s3 = PythonOperator(
    dag=dag,
    task_id="spark_script_to_s3",
    python_callable=_local_to_s3,
    op_kwargs={
        "file_name": "./dags/scripts/spark/loan_tracker.py",
        "key": "scripts/loan_tracker.py",
        "bucket_name": BUCKET_NAME,
    },
)

start_emr_loan_tracker_classification_script = EmrAddStepsOperator(
    dag=dag,
    task_id="start_emr_loan_tracker_classification_script",
    job_flow_id=EMR_ID,
    aws_conn_id="aws_default",
    steps=EMR_STEPS,
    params={
        "BUCKET_NAME": BUCKET_NAME,
        "raw_loan_tracker": "raw/loan_tracker",
        "loans_script": "scripts/loan_tracker.py",
        "stage_loan_tracker": "stage/loan_tracker",
    },
    depends_on_past=True,
)

last_step = len(EMR_STEPS) - 1

wait_for_loan_tracker_transformation = EmrStepSensor(
    dag=dag,
    task_id="wait_for_loan_tracker_transformation",
    job_flow_id=EMR_ID,
    step_id='{{ task_instance.xcom_pull\
        ("start_emr_loan_tracker_classification_script", key="return_value")['
    + str(last_step)
    + "] }}",
    depends_on_past=True,
)

generate_loan_tracker_metric = DummyOperator(
    task_id="generate_loan_tracker_metric", dag=dag)

end_of_data_pipeline = DummyOperator(task_id="end_of_data_pipeline", dag=dag)

(
    [
        loan_tracker_to_raw_data_lake,
        spark_script_to_s3,
    ]
    >> start_emr_loan_tracker_classification_script
    >> wait_for_loan_tracker_transformation
    >> generate_loan_tracker_metric
    >> end_of_data_pipeline
)
