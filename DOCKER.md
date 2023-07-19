
## Docker Setup

We also provide a Dockerfile to run MorphQ in a Docker container.

1. To build the Docker image, run the following command:
    ```bash
    docker build -t morphq .
    ```
1. To run the Docker container, run the following command:
    ```bash
    docker run -it --rm -p 8888:8888 morphq
    ```

Optionally: To avoid the build process, you can also use the ready made Docker image from Docker Hub:
```bash
docker run -it --rm -p 8888:8888 mattepalte/morphq:latest
```

### LEVEL 1: Reproduce the Paper Figures

1. To run the notebook in the Docker container, run the following command:
    ```bash
    jupyter notebook --allow-root --no-browser --ip=0.0.0.0 --port=8888
    ```
1. Then open the link that is printed in the terminal in your browser. Note that the link will look something like this: `http://127.0.0.1:8888/?token=6819f647f19859d9e92013a41f52f49d6ffed633e7b68657`.
1. Open the `notebooks/RQs_Reproduce_Analysis_Results_Level_1.ipynb` notebook.
1. Run the notebook top-to-bottom.
1. Congratulations! You reproduced all the paper figures based on our experimental data.


### LEVEL 2: Run MorphQ For a New Testing Campaign

1. Generate a new configuration file with the following command:
    ```bash
    python3 -m lib.generate_new_config --version 01
    ```
1. Select `morphq_demo.yaml` as the base configuration file.
1. Run the following command to run MorphQ with the new configuration:
    ```bash
    python3 -m lib.qmt config/qmt_v01.yaml
    ```
1. Congratulations! You successfully run MorphQ.

**Persisting Data**

Note that your newly generated data will be transient in this Docker, thus if you are interested in accessing them need to mount a folder on your host mahcine (aka laptop) as a volume in the docker container.

Follow these steps, while in the root folder of the cloned repository:
1. Create a data folder to store all the docker generated data:
    ```bash
    mkdir data_docker
    ```
2. Run the following command to run MorphQ with the new configuration (if you use another OS instead of Ubuntu, the syntax might be a little different, see this [link](https://stackoverflow.com/a/41489151)):
    ```bash
    docker run -it --rm -p 8888:8888 -v $(pwd)/data_docker:/opt/data mattepalte/morphq:latest
    ```
3. Run the steps in Level 2 above:
    ```bash
    python3 -m lib.generate_new_config --version 01 # select morphq_demo.yaml as the base configuration file
    python3 -m lib.qmt config/qmt_v01.yaml
    ```
4. When enough data is generated, stop MorphQ by pressing `Ctrl+C`, and type `exit` to exit the docker container.
4. You can now access the data in the `data_docker` folder on your laptop even when the docker is not running.


### LEVEL 3: Run MorphQ in the Evaluation of a New Fuzzer


In case you plan to evaluate your new fuzzer against MorphQ, please follow the steps below.

#### Qiskit Version
You might want to test a different Qiskit version than the one used in the original MorphQ evaluation.
1. Change the qiskit version (e.g. `qiskit==0.43.1`) in the [requirements.txt](requirements.txt) file.
1. Build the Docker image again, running this command from the repo root:
    ```bash
    docker build -t morphq-as-competitor -f dockerfiles/as_competitor/Dockerfile .
    ```

#### Coverage Metric
Since MorphQ is not using any feedback information on the coverage and the coverage instrumentation is slowing the fuzzer without any good reason, the coverage can also be computed offline after the MorphQ run has finished.
If you need to compute the coverage while fuzzing you can do that by setting the `track_coverage` flag in the configuration file to `True` (see [morphq_as_competitor.yaml](config/template/morphq_as_competitor.yaml)).

IMPORTANT: note that the results in the original paper are computed with the `track_coverage` flag set to `True`.

We recommend to compute it offline since this can speed up the process.


#### Run MorphQ: May the Best Fuzzer Win!
1. Run the container with the following command (from the repo root), note that we also mount the data and config folders, to persist the data and to be able to access the configuration files even when the docker is not running:
    ```bash
    docker run -it --rm --user $(id -u yourusername):$(id -g yourusername) -v $(pwd)/data:/opt/data  -v $(pwd)/lib:/opt/lib -v $(pwd)/config:/opt/config -v $(pwd)/.gitignore:/opt/.gitignore morphq-as-competitor

    # Example
    docker run -it --rm --user $(id -u paltenmo):$(id -g paltenmo) -v $(pwd)/data:/opt/data  -v $(pwd)/lib:/opt/lib -v $(pwd)/config:/opt/config -v $(pwd)/.gitignore:/opt/.gitignore morphq-as-competitor
    ```
    Note: replace `yourusername` with your username.
1. Generate a new configuration file with the following command:
    ```bash
    # [IN THE DOCKER CONTAINER]
    python3 -m lib.generate_new_config --version 01
    ```
1. Select `morphq_as_competitor.yaml` as the base configuration file.
1. Run the following command to run MorphQ with the new configuration:
    ```bash
    # [IN THE DOCKER CONTAINER]
    python3 -m lib.qmt config/qmt_v01.yaml
    ```
1. Congratulations! You successfully run MorphQ.
1. We recommend a campaign of at least 48 hours to have a fair comparison with MorphQ.


#### Comparison with MorphQ
If you used the default coverage setup (`track_coverage=false`), once you are done with the fuzzing campaign, you can compute the coverage on the generated programs by running the following command:
```bash
# [IN THE DOCKER CONTAINER]
python -m lib.coverage.reorder_files -i data/qmt_v01/
```
This will first extract all the generated files in order of generation in the `coverage_offline` folder, each file will be called: `1.fuzz`, `2.fuzz`, etc.

```bash
# [IN THE DOCKER CONTAINER]
python -m lib.coverage.cumulative_coverage --target-folder data/qmt_v01/programs_sorted --output-folder data/qmt_v01/cumulative_coverage -n 50 --timeout 10 --file-extension .fuzz
```
Note that by default we track the coverage on all the packages in the `site-packages` folder starting with `qiskit`, if you want to change this behavior you can do that by setting the `--packages-to-track` argument, for example:
```bash
# [IN THE DOCKER CONTAINER]
python -m lib.coverage.cumulative_coverage --target-folder data/qmt_v01/programs_sorted --output-folder data/qmt_v01/cumulative_coverage -n 10 --timeout 10 --file-extension .fuzz --packages-to-track qiskit_aer --packages-to-track qiskit_ibmq_provider-0.20.2.dist-info
```

Then the `coverage.py` tool will compute the coverage for each generated program and then combine the results in a cumulative way.
For example, if you choose a step of 10 program it will give you the coverage of the first 10 programs, then the coverage of the first 20 programs, etc.
The output will be stored in a csv file called `cumulative_coverage.csv` in the `cumulative_coverage` folder, ready to be plot with your favorite tool.
