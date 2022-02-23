FROM node:16-alpine3.15


# Install bash, python and pip 
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 bash && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

COPY requirements.txt /
WORKDIR /
RUN pip3 install --no-cache-dir -r requirements.txt

# copy source code
COPY  cdk-config.yml /
COPY pipe.yml /
COPY pipe /
# COPY sample /

ENTRYPOINT ["python3", "/pipe.py"]
