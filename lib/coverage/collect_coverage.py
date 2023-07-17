import glob
import json
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

import click
import coverage
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from rich.traceback import install

install()
CURRENT_TIME = time.time()
DEBUG = False

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)


def natural_sort_key(s):
    _nsre = re.compile("([0-9]+)")
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)
    ]


def collect_coverage_single_files(
    folder: str, output: str, path_cover_file: str
):
    """Collect the coverage for each single file in the given folder."""
    # create the output directory if it doesn't exist
    if not os.path.exists(output):
        os.makedirs(output)

    abs_folder = os.path.abspath(folder)
    abs_output = os.path.abspath(output)
    abs_path_rcfile = os.path.abspath(path_cover_file)

    file_paths = glob.glob(folder + "/*.fuzz")
    file_paths.sort(key=natural_sort_key)
    abs_file_paths = [os.path.abspath(file_path) for file_path in file_paths]

    print(f"Found {len(file_paths)} files to fuzz.")
    print("e.g. ", file_paths[0], f"({abs_file_paths[0]})")
    with Progress(
        TextColumn("Compute coverage • [progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ) as p:
        task = p.add_task("Coverage", total=len(abs_file_paths))
        for file_path in abs_file_paths:
            filename = os.path.basename(file_path)
            # replace env var COVERAGE_FILE with the absolute path of the file followed by ".coverage"
            cmd_compute_coverage = f"docker run -v {abs_folder}:/opt/data_files -v {abs_output}:/opt/coverage -v {abs_path_rcfile}:/opt/coverage/rcfile.cover -e COVERAGE_FILE=/opt/coverage/.coverage.{filename} -e COVERAGE_RCFILE=/opt/coverage/rcfile.cover --rm morphq-as-competitor coverage run /opt/data_files/{filename}"
            # equivalent command not in docker
            # cmd_compute_coverage = f"coverage run --source={abs_packages_to_track_comma} {file_path}"
            if DEBUG:
                print(f"Running command: {cmd_compute_coverage}")
            exit_code = subprocess.run(
                cmd_compute_coverage,
                shell=True,
                encoding="utf-8",
                text=True,
                capture_output=True,
            )
            if exit_code.returncode != 0:
                print(exit_code.stderr)
            # increase the progress bar of 1
            p.update(task, advance=1)


def compute_cumulative_coverage(
    path_coverage_dir: str, path_output_dir: str, every_n_files: int = 10
) -> str:
    """Compute the coverage reports at steps of n.

    if n=10, then compute the coverage for the first 10 files, then for the
    first 20 files, first 30 files, etc.

    It returns the path to the cumulative coverage folder, each subfolder
    contains a coverage report for the first n files.
    """
    coverage_files = glob.glob(path_coverage_dir + "/.coverage.*.fuzz.*")
    regex = "(\d+).fuzz."  # match the number in the name
    sorted_coverage_files = sorted(
        coverage_files, key=lambda x: int(re.search(regex, x).group(1))
    )

    # create a new folder cumulative in the output folder
    cumulative_folder = path_output_dir
    if not os.path.exists(cumulative_folder):
        os.makedirs(cumulative_folder)

    with Progress(
        TextColumn(
            "Compute coverage ({task.description}) • [progress.percentage]{task.percentage:>3.0f}%"
        ),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ) as p:
        split_task = p.add_task("Split in folders", total=len(sorted_coverage_files))
        sum_task = p.add_task("Cumulative Sum", total=len(sorted_coverage_files))
        for i, filepath in enumerate(sorted_coverage_files):

            if i % every_n_files == 0:
                # aggregate the coverage files lower than the current integer
                # e.g. if i=0, aggregate the first file, if i=1, aggregate the first
                # two files, etc.
                relevant_files = sorted_coverage_files[: i + 1]

                # create subfolder in cumulative folder with these files
                subfolder = os.path.join(cumulative_folder, str(i))
                if not os.path.exists(subfolder):
                    os.makedirs(subfolder)

                # copy the relevant files to the subfolder
                for file in relevant_files:
                    shutil.copy(file, subfolder)
                p.update(split_task, advance=every_n_files)

        # compute the coverage for each subfolder

        subfolders = [
            subfolder_name
            for subfolder_name in os.listdir(cumulative_folder)
            if os.path.isdir(os.path.join(cumulative_folder, subfolder_name))
        ]
        for j, subfolder_name in enumerate(subfolders):
            # for each file combine
            path_subfolder = os.path.join(cumulative_folder, subfolder_name)
            abs_path_subfolder = os.path.abspath(path_subfolder)
            abs_output_coverage_file = os.path.join(abs_path_subfolder, ".coverage")
            # combine the coverage files in the subfolder
            cmd_combine = f"coverage combine --data-file={abs_output_coverage_file} {abs_path_subfolder}"
            t_start_combine = time.time()
            if DEBUG:
                print(f"Running command: {cmd_combine}")
            exit_code = subprocess.run(
                cmd_combine,
                shell=True,
                encoding="utf-8",
                text=True,
                capture_output=True,
            )
            if exit_code.returncode != 0:
                print(exit_code.stderr)
            t_end_combine = time.time()
            duration_combine = t_end_combine - t_start_combine
            if DEBUG:
                print(f"Combine took {duration_combine} seconds")
            # JSON report - ALTERNATIVE - NOT USED
            # json_file = os.path.join(path_subfolder, "coverage.json")
            # abs_json_file = os.path.abspath(json_file)
            # cmd_json = f"docker run -v {abs_output_coverage_file}:/.coverage -v {abs_path_subfolder}:/coverage --rm morphq-as-competitor coverage json -o /coverage/coverage.json"

            # generate the xml report
            xml_file = os.path.join(path_subfolder, "coverage.xml")
            abs_xml_file = os.path.abspath(xml_file)
            cmd_xml = f"docker run -v {abs_output_coverage_file}:/opt/.coverage -v {abs_path_subfolder}:/opt/coverage --rm morphq-as-competitor coverage xml -o /opt/coverage/coverage.xml"
            t_start_xml = time.time()
            # docker run -v /home/paltenmo/projects/FuzzAll/Results/qiskit_basic/test/.coverage.0.fuzz:/.coverage -v /home/paltenmo/projects/FuzzAll/Results/qiskit_basic/test:/coverage --rm morphq-as-competitor coverage xml -o /coverage/coverage.xml
            if DEBUG:
                print(f"Running command: {cmd_xml}")
            exit_code = subprocess.run(
                cmd_xml,  # cmd_json,  # JSON report - ALTERNATIVE - NOT USED
                shell=True,
                encoding="utf-8",
                text=True,
                capture_output=True,
            )
            if exit_code.returncode != 0:
                print(exit_code.stderr)
            print(exit_code.stdout)
            t_end_xml = time.time()
            duration_xml = t_end_xml - t_start_xml
            if DEBUG:
                print(f"XML took {duration_xml} seconds")
            p.update(sum_task, advance=every_n_files)

        return cumulative_folder


def create_csv(path_cumulative_folder: str, path_dir_csv_output: str) -> str:
    """Create a csv file with the coverage information as function of files.

    We assume that the cumulative folder has subfolders with structure:
    cumulative_folder
        0
            .coverage
            coverage.xml
        10
            .coverage
            coverage.xml
        20
            .coverage
            coverage.xml
        ...

    It returns the path to the csv file.
    """
    all_records = []
    subfolders = [
        subfolder_name
        for subfolder_name in os.listdir(path_cumulative_folder)
        if os.path.isdir(os.path.join(path_cumulative_folder, subfolder_name))
    ]
    for j, subfolder_name in enumerate(subfolders):
        path_subfolder = os.path.join(path_cumulative_folder, subfolder_name)
        path_xml_file = os.path.join(path_subfolder, "coverage.xml")

        tree = ET.parse(path_xml_file)
        root = tree.getroot()
        total_coverage = float(root.attrib["line-rate"])
        # JSON report - ALTERNATIVE - NOT USED
        # report = json.load(open(abs_json_file))
        # total_coverage = report["totals"]["percent_covered"]
        n_files = int(subfolder_name)
        all_records.append({"n_files": n_files, "perc_total_coverage": total_coverage})

    df = pd.DataFrame.from_records(all_records)
    output_csv = os.path.join(path_dir_csv_output, "cumulative_coverage.csv")
    df.to_csv(output_csv, index=False)
    return output_csv


def plot_data(path_csv: str, path_output: str):
    """Plot the data in the csv file and save the plot in the path_output."""
    df = pd.read_csv(path_csv)
    df = df.sort_values(by="n_files")
    df.plot(x="n_files", y="perc_total_coverage")
    plt.savefig(os.path.join(path_output, "cumulative_coverage.png"))


@click.command()
@click.option(
    "--folder",
    "-f",
    default=".",
    help="The folder containing the python files to compute coverage for.",
)
@click.option(
    "--output",
    "-o",
    default="coverage",
    help="The folder to save the coverage to.",
)
@click.option(
    "--every-n-files",
    "-n",
    default=10,
    help="The number of files to aggregate in each step.",
)
@click.option(
    "--path-cover-file",
    "-c",
    help="The path to the cover file.",
)
@click.option(
    "--create-plot",
    "-p",
    default=True,
    help="Whether to create a plot of the coverage.",
)
def collect_coverage(
    folder: str,
    output: str,
    every_n_files: int,
    path_cover_file: str,
    create_plot: bool,
):
    """Collect the coverage of the given folder and save it to the given output
    directory.

    The output directory must be empty.
    """

    # proceed only if the output directory is empty
    if os.path.exists(output):
        if len(os.listdir(output)) != 0:
            print(f"The output directory is not empty: {output}")
            return

    path_single_file_coverage = os.path.join(output, "single_file_coverage")

    collect_coverage_single_files(
        folder=folder,
        output=path_single_file_coverage,
        path_cover_file=path_cover_file,
    )

    path_cumulative_folder = os.path.join(output, "cumulative_coverage")

    compute_cumulative_coverage(
        path_coverage_dir=path_single_file_coverage,
        path_output_dir=path_cumulative_folder,
        every_n_files=every_n_files,
    )

    path_csv = create_csv(
        path_cumulative_folder=path_cumulative_folder,
        path_dir_csv_output=output,
    )

    if create_plot:
        plot_data(
            path_csv=path_csv,
            path_output=output,
        )


if __name__ == "__main__":
    collect_coverage()
