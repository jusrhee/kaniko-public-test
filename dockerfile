FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y python3 python3-pip python3-dev build-essential
COPY ./requirements.txt /app/server/requirements.txt
WORKDIR /app/server
RUN pip3 install -r requirements.txt
COPY . /app/server
EXPOSE 80
ENTRYPOINT ["python3"]
CMD ["server.py"]