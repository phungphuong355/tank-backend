import json
import os
import pandas as pd

from config import UPLOADS, ALLOWED_EXTENSIONS


# allow file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_file_project(filename: str) -> dict:
    filename = filename.replace(" ", "").lower()

    if not os.path.exists(f"{UPLOADS}/{filename}"):
        os.makedirs(f"{UPLOADS}/{filename}")

    project = dict(
        interval=24.0,  # time interval in hour : float
        basin=f'{filename}.basin.json',  # basin path - json-file
        precipitation=f'{filename}.pr.csv',  # precipitation path - csv file
        evapotranspiration=f'{filename}.et.csv',  # evapotranspiration path - csv file
        discharge=f'{filename}.q.csv',  # observer discharge path - csv file
        result=f'{filename}.result.csv',  # output file for discharge - csv file
        statistics=f'{filename}.stats.json'  # statistics calculated form observed discharge - json-file
    )

    project_file_path = os.path.join(f"{UPLOADS}/{filename}", f'{filename}.project.json')

    with open(project_file_path, 'w') as project_file:
        f = project_file.write(json.dumps(project, indent=2))

    return f


def create_basin_file(filename: str) -> dict:
    filename = filename.replace(" ", "").lower()

    basin = dict(
        basin_def={
            "BAHADURABAD": {
                "type": "Subbasin",
                "upstream": [],
                "parameters": {
                    "t0_is": 0.01,
                    "t0_boc": 0.1,
                    "t0_soc_uo": 0.1,
                    "t0_soc_lo": 0.1,
                    "t0_soh_uo": 75.0,
                    "t0_soh_lo": 0.0,
                    "t1_is": 0.01,
                    "t1_boc": 0.01,
                    "t1_soc": 0.01,
                    "t1_soh": 0.0,
                    "t2_is": 0.01,
                    "t2_boc": 0.01,
                    "t2_soc": 0.01,
                    "t2_soh": 0.0,
                    "t3_is": 0.01,
                    "t3_soc": 0.01
                },
                "area": 0.0
            },
            "Reach": {
                "type": "Reach",
                "upstream": [
                    "BAHADURABAD"
                ],
                "parameters": {
                    "k": 2.0,
                    "x": 0.3
                }
            },
            "Junction": {
                "type": "Junction",
                "upstream": [
                    "Reach"
                ],
                "parameters": {}
            },
            "Sink": {
                "type": "Sink",
                "upstream": [
                    "Junction"
                ],
                "parameters": {}
            }
        },
        root_node=[
            "BAHADURABAD"
        ]
    )

    basin_file_path = os.path.join(f"{UPLOADS}/{filename}", f'{filename}.basin.json')

    with open(basin_file_path, 'w') as project_file:
        f = project_file.write(json.dumps(basin, indent=2))

    return f


def create_stats_file(filename: str) -> dict:
    filename = filename.replace(" ", "").lower()

    stats = dict(
        BAHADURABAD={
            "RMSE": 0.0,
            "NSE": 0.0,
            "R2": 0.0,
            "PBIAS": 0.0
        }
    )

    stats_file_path = os.path.join(f"{UPLOADS}/{filename}", f'{filename}.stats.json')

    with open(stats_file_path, 'w') as project_file:
        f = project_file.write(json.dumps(stats, indent=2))

    return stats


def create_csv_file(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    filename = filename.replace(" ", "").lower()

    df.columns = ["Time", "precipitation", "evapotranspiration", "discharge"]

    df['Time'] = pd.to_datetime(df['Time'], utc=True)

    pr_csv = df.drop(['evapotranspiration', 'discharge'], axis=1)
    et_csv = df.drop(['precipitation', 'discharge'], axis=1)
    q_csv = df.drop(['evapotranspiration', 'precipitation'], axis=1)
    result_csv = df.drop(['evapotranspiration', 'precipitation'], axis=1)

    pr_csv.columns, \
        et_csv.columns, \
        q_csv.columns, \
        result_csv.columns = ["Time", "BAHADURABAD"], \
        ["Time", "BAHADURABAD"], \
        ["Time", "BAHADURABAD"], \
        ["Time", "BAHADURABAD"]

    result_csv.BAHADURABAD = [1]*len(result_csv.iloc[:,0])

    pr_csv.to_csv(f"{UPLOADS}/{filename}/{filename}.pr.csv", index=False)
    et_csv.to_csv(f"{UPLOADS}/{filename}/{filename}.et.csv", index=False)
    q_csv.to_csv(f"{UPLOADS}/{filename}/{filename}.q.csv", index=False)
    result_csv.to_csv(f"{UPLOADS}/{filename}/{filename}.result.csv", index=False)

    return df


def read_stats_file(stats_file: str) -> dict:
    if not os.path.exists(stats_file):
        raise Exception('provided basin file doesnt exists')

    with open(stats_file, 'r') as stats_file_rd_buffer:
        stats = json.load(stats_file_rd_buffer)

        # check if basin file is  okay [will work on it later]

        return stats


def change_data_to_json_file(file: pd.DataFrame) -> dict:

    data = file.to_dict(orient='records')

    return data
