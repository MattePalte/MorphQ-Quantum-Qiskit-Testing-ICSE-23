FROM continuumio/miniconda3

# Move to the opt directory
WORKDIR /opt/

# download the environment from the original repo
RUN conda create -n MorphQAsCompetitor python=3.10
RUN echo "source activate MorphQAsCompetitor" > ~/.bashrc
ENV PATH /opt/conda/envs/MorphQAsCompetitor/bin:$PATH

# install required packages from the requirements file
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy software module lib
COPY lib /opt/lib
# copy config files
COPY config /opt/config
# Create data directory
RUN mkdir data
# copy .gitignore
COPY .gitignore /opt/.gitignore


# CMD ["python"]
CMD ["/bin/bash"]
