FROM matteobusi/alvie

USER root

WORKDIR /home/alvie/alvie-cli


RUN mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && \
    apt-get install -y python3 python3-pip python-is-python3 python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv venv

ENV PATH="./venv/bin:$PATH"

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["/bin/bash"]