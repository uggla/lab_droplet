#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import json
import jinja2
from flask import Flask
from flask import jsonify
from flask import request
from flask import send_from_directory
from flask_sockets import Sockets
from api_exception import InvalidUsage
from flask_httpauth import HTTPBasicAuth
from flask_restful import abort
from pprint import pprint
import droplet


class Reservation(object):
    def __init__(self):
        self.file = "reservation.json"
        self.data = None

        # read json file
        try:
            with open(self.file, "r") as json_data:
                self.data = json.load(json_data)
                json_data.close()
        except IOError:
            self.data = {}
            self.save()

    def save(self):
        with open(self.file, "w") as json_data:
            json_data.write(json.dumps(self.data))
            json_data.close()

    def reserve(self, uuid, owner):
        self.data.update({uuid: owner})
        self.save()

    def get(self, uuid):
        try:
            return self.data[uuid]
        except KeyError:
            return ""

    def release(self, uuid):
        try:
            del self.data[uuid]
            self.save()
        except KeyError:
            pass


ENV = ("DIGITALOCEAN_TOKEN", "PUBKEY", "LABUSER", "LABPASSWD")
for item in ENV:
    VAR = os.getenv(item)
    if not VAR:
        print("Please set {} environment variable.".format(item))
        sys.exit(1)

app = Flask(__name__)
sockets = Sockets(app)
auth = HTTPBasicAuth()

# Initialize reservation
resa = Reservation()

users = {os.getenv("LABUSER"): os.getenv("LABPASSWD")}


@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)
    return None


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
@auth.login_required
def index():
    html = render_template("user.html")
    return html


@app.route("/create_droplet", methods=["POST"])
@auth.login_required
def create_droplet():
    if (
        not request.form["InputAccount"]
        or not request.form["InputPubSSH"]
        or not re.match(r"^ssh-rsa .+$", request.form["InputPubSSH"])
        or not re.match(r"\w{4,}", request.form["InputAccount"])
    ):  # noqa
        abort(400, message="Bad request")
    pprint(request.form["InputAccount"])
    pprint(request.form["InputPubSSH"])
    pprint(request.form["InputDistro"])
    pprint(request.form["InputFlavor"])
    vmid = new_droplet(
        request.form["InputAccount"],
        request.form["InputPubSSH"],
        request.form["InputDistro"],
        request.form["InputFlavor"],
    )
    html = render_template("droplet.html", vmid)
    return html


def new_droplet(account, pubssh, distro, flavor):
    ANIMALS_LIST_URL = "https://raw.githubusercontent.com/hzlzh/Domain-Name-List/master/Animal-words.txt"  # noqa
    ADJECTIVES_LIST_URL = "https://raw.githubusercontent.com/gef756/namegen/master/adjectives.txt"  # noqa
    TAG = ["docker", account]
    REGION = "ams3"  # Amsterdam 3
    if distro == "centos":
        IMAGE = "centos-7-x64"
    elif distro == "ubuntu":
        IMAGE = "ubuntu-16-04-x64"
    elif distro == "docker":
        IMAGE = "docker-18-04"

    if flavor == "1GB":
        DROPLET_SIZE = "s-1vcpu-1gb"
    elif flavor == "4GB":
        DROPLET_SIZE = "s-2vcpu-4gb"

    TOKEN = os.getenv("DIGITALOCEAN_TOKEN")

    userkey = droplet.digitalocean.SSHKey(token=TOKEN)
    userkey.load_by_pub_key(pubssh)

    if not userkey.id:
        userkey = droplet.digitalocean.SSHKey(
            token=TOKEN, name=account, public_key=pubssh
        )
        userkey.create()

    # admkeys = droplet.get_ssh_keys(TOKEN)
    admkey = droplet.digitalocean.SSHKey(token=TOKEN)
    admkey.load_by_pub_key(os.getenv("PUBKEY"))

    keys = [userkey, admkey]
    vm = droplet.digitalocean.Droplet(
        token=TOKEN,
        name=droplet.generate_random_name(
            ADJECTIVES_LIST_URL, ANIMALS_LIST_URL
        ),
        region=REGION,
        image=IMAGE,
        size_slug=DROPLET_SIZE,
        tags=TAG,
        ssh_keys=keys,
    )
    vm.create()
    return vm.id


def add_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type,Authorization"
    )


@sockets.route("/vmstatus")
def vmstatus(ws):
    TOKEN = os.getenv("DIGITALOCEAN_TOKEN")
    data = json.loads(ws.receive())
    pprint(data)
    vm = droplet.get_droplet(TOKEN, data["vmid"])
    droplet.wait_completion(vm)
    # Reload status
    vm = droplet.get_droplet(TOKEN, data["vmid"])
    pprint(vm)
    print("Droplet id:   {}".format(vm.id))
    print("Droplet name: {}".format(vm.name))
    print("Droplet ip:   {}".format(vm.ip_address))
    data = {"vmid": vm.id, "vmname": vm.name, "vmip": vm.ip_address}
    ws.send(json.dumps(data))


@app.route("/css/<path>")
def send_css(path):
    return send_from_directory("templates/css", path)


@app.route("/img/<path>")
def send_img(path):
    return send_from_directory("templates/img", path)


def render_template(template, values=None):
    # Initialize Template system (jinja2)
    templates_path = "templates"
    jinja2_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_path)
    )
    try:
        template = jinja2_env.get_template(template)
    except jinja2.exceptions.TemplateNotFound as e:
        print(
            'Template "{}" not found in {}.'.format(
                e.message, jinja2_env.loader.searchpath[0]
            )
        )

    if values is None:
        data = template.render()
    else:
        data = template.render(r=values)

    return data


if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(("", 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
