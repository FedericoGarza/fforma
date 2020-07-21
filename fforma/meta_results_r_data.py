#!/usr/bin/env python
# coding: utf-8

import requests
import os
import tarfile
import subprocess

import pandas as pd

from tqdm import tqdm
from fforma.m4_data import prepare_m4_data, prepare_full_m4_data
from fforma.utils import wide_to_long

URL_M4 = 'https://github.com/pmontman/M4metaresults/releases/download/v0.0.0.9000/M4metaresults_0.0.0.9000.tar.gz'
URL_M3 = 'https://github.com/FedericoGarza/meta-data/releases/download/v0.0.0.9000/m3-meta-data.pickle'
URL_TOURISM = 'https://github.com/FedericoGarza/meta-data/releases/download/v0.0.0.9001/tourism-meta-data.pickle'

def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

################################################################################
#################### M4 processes
###############################################################################

def maybe_download_decompress_m4(directory):
    """Download the data from M4's website, unless it's already here.

    Parameters
    ----------
    directory: str
        Custom directory where data will be downloaded.
    """
    root_fforma_data = directory + '/m4_meta_data'
    if not os.path.exists(root_fforma_data):
        os.mkdir(root_fforma_data)

    compressed_data_directory = root_fforma_data + '/raw'

    if not os.path.exists(compressed_data_directory):
        os.mkdir(compressed_data_directory)

    filename = URL_M4.split('/')[-1]
    filepath = os.path.join(compressed_data_directory, filename)

    if not os.path.exists(filepath):
        # Streaming, so we can iterate over the response.
        r = requests.get(URL_M4, stream=True)
        # Total size in bytes.
        total_size = int(r.headers.get('content-length', 0))
        block_size = 1024 #1 Kibibyte
        t = tqdm(total=total_size, unit='iB', unit_scale=True)

        with open(filepath, 'wb') as f:
            for data in r.iter_content(block_size):
                t.update(len(data))
                f.write(data)

        t.close()

        if total_size != 0 and t.n != total_size:
            print("ERROR, something went wrong")

        size = os.path.getsize(filepath)
        print('Successfully downloaded', filename, size, 'bytes.')

    if not data_already_present_m4(directory, kind='decompressed'):
        decompressed_data_directory = compressed_data_directory + '/decompressed_data'

        tar = tarfile.open(filepath, 'r:gz')
        tar.extractall(path=decompressed_data_directory)
        tar.close()

        print('Successfully decompressed ', decompressed_data_directory)

def data_already_present_m4(directory, kind):
    """
    kind: str
        Can be 'r' o 'decompressed'.
    """
    if kind == 'r':
        main_dir = '/m4_meta_data/processed_data'
        needed_data = (f'{main_dir}/train-features.csv',
                       f'{main_dir}/train-ff.csv',
                       f'{main_dir}/train-xx.csv',
                       f'{main_dir}/test-features.csv',
                       f'{main_dir}/test-ff.csv')
    elif kind == 'decompressed':
        main_dir = '/m4_meta_data/raw/decompressed_data/M4metaresults/data'
        needed_data = (f'{main_dir}/submission_M4.rda',
                       f'{main_dir}/meta_M4.rda',
                       f'{main_dir}/model_M4.rda')

    present = [os.path.exists(directory + dir) for dir in needed_data]

    present = all(present)

    return present

def prepare_fforma_data_m4(directory, dataset_name=None):

    #Check downloaded data
    maybe_download_decompress_m4(directory)

    #Prepare data from R
    if not data_already_present_m4(directory, kind='r'):
        cmd = f'Rscript ./fforma/R/prepare_data_m4.R "{directory}"'
        res_r = os.system(cmd)

        assert res_r == 0, 'Some error happened with R processing'

    root_processed_data = directory + '/m4_meta_data/processed_data'

    X_train_df = pd.read_csv(root_processed_data + '/train-features.csv')
    preds_train_df = pd.read_csv(root_processed_data + '/train-ff.csv')
    y_train_df = pd.read_csv(root_processed_data + '/train-xx.csv')

    X_test_df = pd.read_csv(root_processed_data + '/test-features.csv')
    preds_test_df = pd.read_csv(root_processed_data + '/test-ff.csv')


    if dataset_name is not None:
        kind = dataset_name[0]

        X_train_df = X_train_df[X_train_df['unique_id'].str.startswith(kind)]
        preds_train_df = preds_train_df[preds_train_df['unique_id'].str.startswith(kind)]
        y_train_df = y_train_df[y_train_df['unique_id'].str.startswith(kind)]

        X_test_df = X_test_df[X_test_df['unique_id'].str.startswith(kind)]
        preds_test_df = preds_test_df[preds_test_df['unique_id'].str.startswith(kind)]
        *_, y_test_df = prepare_m4_data(dataset_name, directory, 100_000)
    else:
        *_, y_test_df = prepare_full_m4_data(directory)


    return X_train_df, preds_train_df, y_train_df, X_test_df, preds_test_df, y_test_df

################################################################################
################# M3 processes
################################################################################

def maybe_download_m3(directory):
    """Download M3's meta-data, unless it's already here.

    Parameters
    ----------
    directory: str
        Custom directory where data will be downloaded.
    """
    root_fforma_data = directory + '/m3_meta_data'
    if not os.path.exists(root_fforma_data):
        os.mkdir(root_fforma_data)

    raw_data_directory = root_fforma_data + '/raw'

    if not os.path.exists(raw_data_directory):
        os.mkdir(raw_data_directory)

    filename = URL_M3.split('/')[-1]
    filepath = os.path.join(raw_data_directory, filename)

    if not os.path.exists(filepath):
        # Streaming, so we can iterate over the response.
        r = requests.get(URL_M3, stream=True)
        # Total size in bytes.
        total_size = int(r.headers.get('content-length', 0))

        block_size = 1024 #1 Kibibyte
        t = tqdm(total=total_size, unit='iB', unit_scale=True)

        with open(filepath, 'wb') as f:
            for data in r.iter_content(block_size):
                t.update(len(data))
                f.write(data)

        t.close()

        if total_size != 0 and t.n != total_size:
            print("ERROR, something went wrong")

        size = os.path.getsize(filepath)
        print('Successfully downloaded', filename, size, 'bytes.')

    return filepath

def prepare_fforma_data_m3(directory, dataset_name=None):

    #Check downloaded data
    filepath = maybe_download_m3(directory)


    X_train_df, preds_train_df, X_test_df, preds_test_df = pd.read_pickle(filepath)

    preds_train_df = preds_train_df.drop('horizon', 1).rename(columns={'y_val': 'y'})
    preds_test_df = preds_test_df.drop('horizon', 1).rename(columns={'y_test': 'y'})

    cols_wide_to_long = ['ds', 'auto_arima_forec', 'ets_forec',
                         'naive_forec', 'nnetar_forec', 'rw_drift_forec',
                         'snaive_forec', 'stlm_ar_forec', 'tbats_forec',
                         'theta_forec', 'y', 'y_hat_naive2']

    preds_train_df = wide_to_long(preds_train_df, cols_wide_to_long)
    preds_test_df = wide_to_long(preds_test_df, cols_wide_to_long)

    preds_train_df, y_train_df = preds_train_df.drop(['y', 'y_hat_naive2'], 1), preds_train_df[['unique_id', 'ds', 'y', 'y_hat_naive2']]
    preds_test_df, y_test_df = preds_test_df.drop(['y', 'y_hat_naive2'], 1), preds_test_df[['unique_id', 'ds', 'y', 'y_hat_naive2']]

    if dataset_name is not None:
        kind = dataset_name[0]

        X_train_df = X_train_df[X_train_df['unique_id'].str.startswith(kind)]
        preds_train_df = preds_train_df[preds_train_df['unique_id'].str.startswith(kind)]
        y_train_df = y_train_df[y_train_df['unique_id'].str.startswith(kind)]

        X_test_df = X_test_df[X_test_df['unique_id'].str.startswith(kind)]
        preds_test_df = preds_test_df[preds_test_df['unique_id'].str.startswith(kind)]
        y_test_df = y_test_df[y_test_df['unique_id'].str.startswith(kind)]


    return X_train_df, preds_train_df, y_train_df, X_test_df, preds_test_df, y_test_df

################################################################################
################# M3 processes
################################################################################

def maybe_download_tourism(directory):
    """Download tourism's meta-data, unless it's already here.

    Parameters
    ----------
    directory: str
        Custom directory where data will be downloaded.
    """
    root_fforma_data = directory + '/tourism_meta_data'
    if not os.path.exists(root_fforma_data):
        os.mkdir(root_fforma_data)

    raw_data_directory = root_fforma_data + '/raw'

    if not os.path.exists(raw_data_directory):
        os.mkdir(raw_data_directory)

    filename = URL_TOURISM.split('/')[-1]
    filepath = os.path.join(raw_data_directory, filename)

    if not os.path.exists(filepath):
        # Streaming, so we can iterate over the response.
        r = requests.get(URL_TOURISM, stream=True)
        # Total size in bytes.
        total_size = int(r.headers.get('content-length', 0))

        block_size = 1024 #1 Kibibyte
        t = tqdm(total=total_size, unit='iB', unit_scale=True)

        with open(filepath, 'wb') as f:
            for data in r.iter_content(block_size):
                t.update(len(data))
                f.write(data)

        t.close()

        if total_size != 0 and t.n != total_size:
            print("ERROR, something went wrong")

        size = os.path.getsize(filepath)
        print('Successfully downloaded', filename, size, 'bytes.')

    return filepath

def prepare_fforma_data_tourism(directory, dataset_name=None):

    #Check downloaded data
    filepath = maybe_download_tourism(directory)


    X_train_df, preds_train_df, X_test_df, preds_test_df = pd.read_pickle(filepath)

    preds_train_df = preds_train_df.drop('horizon', 1).rename(columns={'y_val': 'y'})
    preds_test_df = preds_test_df.drop('horizon', 1).rename(columns={'y_test': 'y'})

    cols_wide_to_long = ['ds', 'auto_arima_forec', 'ets_forec',
                         'naive_forec', 'nnetar_forec', 'rw_drift_forec',
                         'snaive_forec', 'stlm_ar_forec', 'tbats_forec',
                         'theta_forec', 'y', 'y_hat_naive2']

    preds_train_df = wide_to_long(preds_train_df, cols_wide_to_long)
    preds_test_df = wide_to_long(preds_test_df, cols_wide_to_long)

    preds_train_df, y_train_df = preds_train_df.drop(['y', 'y_hat_naive2'], 1), preds_train_df[['unique_id', 'ds', 'y', 'y_hat_naive2']]
    preds_test_df, y_test_df = preds_test_df.drop(['y', 'y_hat_naive2'], 1), preds_test_df[['unique_id', 'ds', 'y', 'y_hat_naive2']]

    if dataset_name is not None:
        kind = dataset_name[0]

        X_train_df = X_train_df[X_train_df['unique_id'].str.startswith(kind)]
        preds_train_df = preds_train_df[preds_train_df['unique_id'].str.startswith(kind)]
        y_train_df = y_train_df[y_train_df['unique_id'].str.startswith(kind)]

        X_test_df = X_test_df[X_test_df['unique_id'].str.startswith(kind)]
        preds_test_df = preds_test_df[preds_test_df['unique_id'].str.startswith(kind)]
        y_test_df = y_test_df[y_test_df['unique_id'].str.startswith(kind)]


    return X_train_df, preds_train_df, y_train_df, X_test_df, preds_test_df, y_test_df


################################################################################
################# Main function
################################################################################

def prepare_fforma_data(directory, dataset_name=None, kind='M4'):
    """
    """
    if kind == 'M4':
        return prepare_fforma_data_m4(directory, dataset_name)
    elif kind == 'M3':
        return prepare_fforma_data_m3(directory, dataset_name)
    elif kind == 'TOURISM':
        return prepare_fforma_data_tourism(directory, dataset_name)
