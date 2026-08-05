FROM python:3.11-slim@sha256:a25f6aeb42924b56064742e12e8b563c7eb07f1ef18e49a806784680f32d8cfe

# no-network task: the verifier cannot pip install at runtime, so pytest is baked
# into the image. Pinned rather than floating, because a verifier whose test runner
# can change under it is not a fixed instrument.
RUN pip install --no-cache-dir pytest==8.3.4 numpy==2.2.1

WORKDIR /root
COPY data /root/data
