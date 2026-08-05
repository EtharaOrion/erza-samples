FROM python:3.11-slim@sha256:a25f6aeb42924b56064742e12e8b563c7eb07f1ef18e49a806784680f32d8cfe

ENV DEBIAN_FRONTEND=noninteractive

# no-network task: the verifier cannot pip install at runtime, so pytest is baked.
# numpy is OPTIONAL for this task (the ERZA-RB1 computation is pure-math, math.erf);
# it is provided only as a convenience for exploratory analysis.
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pytest==8.3.2 \
    pytest-json-ctrf==0.3.5

WORKDIR /root
COPY data /root/data
