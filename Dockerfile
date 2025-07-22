ARG NODE_TAG
FROM node:${NODE_TAG}

# Install python3, pip and bash
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 py3-pip bash && \
    ln -sf python3 /usr/bin/python

WORKDIR /

COPY pipe /

# Configure virtual env
RUN python3 -m venv /venv && \
    . /venv/bin/activate && \
    PIP_CONSTRAINT=cython_constraint.txt pip install --no-cache-dir -r requirements.txt
ENV PATH="/venv/bin:$PATH"

RUN corepack enable yarn

USER node

ENTRYPOINT ["python", "/pipe.py"]
CMD ["--config", "/cdk-config.yml"]