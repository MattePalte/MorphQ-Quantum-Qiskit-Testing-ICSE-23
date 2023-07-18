
CLEAN_GLOBALS = globals().copy()
CLEAN_LOCALS = locals().copy()

import os
import re
import xml.etree.ElementTree as ET
import click
import coverage
import pandas as pd
from typing import List, Dict, Any, Tuple
from lib.utils import break_function_with_timeout
import time
import matplotlib.pyplot as plt


def sandboxed_exec(python_code: str, data_file: str = None, config_file: str = None):
    """Execute python code in a sandboxed environment."""
    import coverage
    coverage.process_startup()
    cov = coverage.Coverage(
        data_file=data_file,
        data_suffix=True,
        config_file=config_file
    )
    cov.load()
    cov.start()
    global CLEAN_GLOBALS
    global CLEAN_LOCALS
    print("Globals: ", globals())
    print("Locals: ", locals())
    # create a tmp globals and locals with the clean ones
    tmp_globals = CLEAN_GLOBALS.copy()
    tmp_locals = CLEAN_LOCALS.copy()
    # execute the code
    try:
        exec(python_code, tmp_globals, tmp_locals)
    except Exception as e:
        print(f"Error: {e}")
    cov.save()
    return


def run_files(
        sorted_files: List[str],
        data_file: str = None,
        config_file: str = None,
        save_coverage_every_n_files: int = None,
        out_folder: str = None,
        timeout: int = None,):
    """Run a list of files in isolated environments."""
    # run each file
    for i, f in enumerate(sorted_files):
        # execute the file
        # backup the globals and locals
        print(f"Running {f}")
        try:
            start_time = time.time()
            print(f"start exec: {start_time}")
            break_function_with_timeout(
                routine=sandboxed_exec,
                seconds_to_wait=timeout,
                message="Timeout.",
                args=[open(f).read(), data_file, config_file]
            )
            # sandboxed_exec(open(f).read(), data_file, config_file)
            end_time = time.time()
            diff = end_time - start_time
            print(f"end exec. duration: {diff} seconds.")
        except Exception as e:
            print(f"Error: {e}")
        if save_coverage_every_n_files is not None and \
                i % save_coverage_every_n_files == 0:
            # save coverage
            cov = coverage.Coverage(
                data_file=data_file,
                data_suffix=True,
                config_file=config_file
            )
            cov.load()
            cov.combine()
            cov.save()
            cov.load()
            # create report for the last n files
            xml_path = os.path.join(out_folder, f"coverage_{i}.xml")
            cov.xml_report(outfile=xml_path)


def create_cumulative_coverage_csv(output_folder: str):
    """Collect the coverage from all the file and create a csv file.

    The files are:
    - coverage_0.xml
    - coverage_10.xml
    - coverage_20.xml
    ...
    Each xml contains the
    """
    all_records = []
    # use regex
    relevant_files = [
        os.path.join(output_folder, f)
        for f in os.listdir(output_folder)
        if re.match(r"coverage_\d+\.xml", f)
    ]
    for j, path_xml_file in enumerate(relevant_files):
        tree = ET.parse(path_xml_file)
        root = tree.getroot()
        total_coverage = float(root.attrib["line-rate"])
        n_files = int(re.search(r"coverage_(\d+)\.xml", path_xml_file).group(1))
        all_records.append({
            "n_files": n_files,
            "perc_total_coverage": total_coverage})
    df = pd.DataFrame.from_records(all_records)
    output_csv = os.path.join(output_folder, "cumulative_coverage.csv")
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
    "--target-folder",
    "-t",
    help="The folder containing the files to cover.",
)
@click.option(
    "--output-folder",
    "-o",
    help="The folder where to save the coverage info.",
)
@click.option(
    "--every-n-files",
    "-n",
    default=1,
    help="Collect coverage info every n files.",
)
@click.option(
    "--timeout",
    "-to",
    default=10,
    help="Timeout for each file (in seconds).",
)
@click.option(
    "--file-extension",
    "-fe",
    default=".fuzz",
    help="The suffix of the files to cover.",
)
@click.option(
    "--packages-to-track",
    "-p",
    default=None,
    multiple=True,
    help="The packages to track in the site-packages folder (use relative names, e.g. qiskit_aer).",
)
def main(target_folder: str, output_folder: str, every_n_files: int, timeout: int, file_extension: str, packages_to_track: List[str]):
    """Collect the coverage info for all packages starting with "qiskit"."""
    # create the output folder
    os.makedirs(output_folder, exist_ok=True)
    # get the site-packages directory
    site_packages = os.path.dirname(os.path.dirname(coverage.__file__))
    if packages_to_track is None:
        # get all the folders starting with "qiskit"
        qiskit_folders = [
            os.path.join(site_packages, f)
            for f in os.listdir(site_packages)
            if f.startswith("qiskit")
        ]
        for f in qiskit_folders:
            print(f)
        packages_to_track = qiskit_folders
    else:
        # add the site-packages folder prefix to the packages_to_track
        packages_to_track = [
            os.path.join(site_packages, f)
            for f in packages_to_track
        ]
    list_of_packages = "\n    ".join(packages_to_track)
    config_file_content = f"""
[run]
branch = True
concurrency = multiprocessing
parallel = True
source =
    {list_of_packages}
"""
    # create the .coveragerc file
    config_file_path = os.path.join(output_folder, ".coveragerc")
    with open(config_file_path, "w") as f:
        f.write(config_file_content)

    data_file = os.path.join(output_folder, ".mycoverage")

    # get all files starting with "to_run"
    files = [
        os.path.join(target_folder, f)
        for f in os.listdir(target_folder)
        if f.endswith(file_extension)]
    sorted_files = sorted(files)

    # list of files to run
    for f in sorted_files:
        print(f)

    # run the files
    run_files(
        sorted_files=sorted_files,
        data_file=data_file,
        config_file=config_file_path,
        save_coverage_every_n_files=every_n_files,
        out_folder=output_folder,
        timeout=timeout
    )

    cov = coverage.Coverage(
        data_file=data_file,
        data_suffix=True,
        config_file=config_file_path
    )
    cov.load()
    cov.combine()
    cov.save()
    cov.load()
    # save file as xml
    xml_path = os.path.join(output_folder, "coverage_final.xml")
    cov.xml_report(outfile=xml_path)

    path_csv = create_cumulative_coverage_csv(output_folder)
    plot_data(path_csv, output_folder)


if __name__ == "__main__":
    main()
