from datetime import datetime, timedelta
from airflow import DAG
from docker.types import Mount
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator
import subprocess
from os import path

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
}


def run_elt_script():
    script_path = "/opt/airflow/elt/elt_script.py"
    result = subprocess.run(
        ["python", script_path],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Script failed with error: {result.stderr}")
    else:
        print(result.stdout)


def get_current_working_directory():
    result = subprocess.run(['pwd'], stdout=subprocess.PIPE, text=True)
    return result.stdout.strip()


def get_dbt_directory():
    return path.join(path.expanduser('~'), ".dbt")


dag = DAG(
    'elt_and_dbt',
    default_args=default_args,
    description='An ELT workflow with dbt',
    start_date=datetime(2024, 6, 17),
    catchup=False
)

task_1 = PythonOperator(
    task_id="run_elt_script",
    python_callable=run_elt_script,
    dag=dag
)

current_working_directory = get_current_working_directory()
dbt_directory = get_dbt_directory()

task_2 = DockerOperator(
    task_id="dbt_run",
    image="ghcr.io/dbt-labs/dbt-postgres:latest",
    command=[
        "run",
        "--profiles-dir",
        "/root",
        "--project-dir",
        "/dbt"
    ],
    auto_remove=True,  # Remove the container once it's done
    docker_url="unix://var/run/docker.sock",
    network_mode="bridge",
    mounts=[
        Mount(source=current_working_directory,
              target="/dbt",
              type='bind'),
        Mount(source=dbt_directory,
              target="/root",
              type='bind'),
    ],
    dag=dag
)

task_1 >> task_2  # Task 1 runs first, task 2 runs seconds
