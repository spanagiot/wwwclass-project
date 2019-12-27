FROM alpine:latest

RUN apk add --update python py-pip
RUN apk add gcc
RUN pip install --upgrade pip
RUN pip install Flask requests bson pymongo uuid redis gunicorn
RUN apk add py-openssl 
RUN apk add libffi-dev
RUN apk add python-dev
RUN apk add linux-headers
RUN apk add musl-dev
RUN apk add openssl-dev 
RUN pip install cryptography
RUN pip install Flask-SSLify
RUN apk add ca-certificates
RUN pip install -U requests[security]
RUN mkdir /wefi
WORKDIR /wefi
COPY . /wefi/.
EXPOSE 80
WORKDIR /wefi
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:80", "wefi:app", "gunicorn-scripts"]
