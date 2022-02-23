FROM node:16-alpine3.15


# Install python and pip 
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

WORKDIR /

# For dev environment
# RUN mkdir -p /app/sample


# copy source code
COPY requirements.txt /
COPY  cdk-config.yml /
COPY pipe.yml /
COPY pipe /
RUN chmod a+x /pipe.py && \
    chown -R node ~/.npm && \
    apk add bash && \
    pip3 install --no-cache-dir -r requirements.txt

USER node

ENTRYPOINT ["python", "/pipe.py"]
CMD ["--config", "/cdk-config.yml"]