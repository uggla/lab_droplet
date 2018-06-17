FROM python:3
LABEL maintainer='uggla@free.fr'
EXPOSE 5000
ENV PYTHONPATH=/usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Running tests
#RUN pytest 
RUN useradd lab
VOLUME /usr/src/app/data
RUN chown -R lab:lab /usr/src/app/data
USER lab
CMD [ "./exec_server.sh" ]
