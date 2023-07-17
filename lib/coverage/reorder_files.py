"""Utility to reorder the generated file as 1.fuzz, 2.fuzz, 3.fuzz, etc.

They are ordered by timestamp and the `source` file is the first (e.g. 1.fuzz),
whereas the `followup` file comes right after (e.g. 2.fuzz).
"""

import os
import click
import pandas as pd
import sqlite3 as sl
from tqdm import tqdm


@click.command()
@click.option('--input-exp-folder', '-i', required=True, type=click.Path(exists=True), help='Path to the experiment folder.')
def reorder(input_exp_folder):
    dir_input = os.path.join(input_exp_folder, 'programs')
    dir_output = os.path.join(input_exp_folder, 'programs_sorted')
    dir_input_source = os.path.join(dir_input, 'source')
    dir_input_followup = os.path.join(dir_input, 'followup')

    # create the output folder
    if not os.path.exists(dir_output):
        os.makedirs(dir_output)

    path_db = os.path.join(input_exp_folder, 'qfl.db')
    print(f"Reading database from {path_db}")
    sql_conn = sl.connect(path_db)

    # read the tables from the database
    df_all = pd.read_sql("SELECT * FROM QFLDATA", sql_conn)

    # sort the files by timestamp abs_start_time
    df_sorted = df_all.sort_values(by=['abs_start_time'])
    sorted_program_ids = df_sorted['program_id'].values
    # copy the files to the output folder
    all_mapping_records = []
    i = 1
    for program_id in tqdm(sorted_program_ids):
        for version_dir in [dir_input_source, dir_input_followup]:
            old_name = f'{program_id}.py'
            new_name = f'{i}.fuzz'
            old_rel_path = os.path.join(version_dir, old_name)
            new_rel_path = os.path.join(dir_output, new_name)
            mapping_record = {
                'old_program_id': program_id,
                'new_program_id': new_name,
                'old_rel_path': old_rel_path,
                'new_rel_path': new_rel_path
            }
            i += 1
            all_mapping_records.append(mapping_record)
            os.system(f'cp {old_rel_path} {new_rel_path}')
            # print(f'cp {old_rel_path} {new_rel_path}')
    df_mapping = pd.DataFrame(all_mapping_records)
    df_mapping.to_csv(os.path.join(input_exp_folder, 'program_order_mapping.csv'), index=False)


if __name__ == '__main__':
    reorder()
