#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import digitalocean
import os
import random
import sys
import time
import requests


def wait_completion(droplet):
    status = ''
    actions = droplet.get_actions()
    while status != 'completed':
        for action in actions:
            action.load()
            # once it shows complete, droplet is up and running
            print(action.status)
            status = action.status
            time.sleep(5)


def retrieve_list(url):
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        print('Fail to connect URL: {}'.format(url))
        sys.exit(1)
    if response.status_code != 200:
        print('Can not get response list.')
        sys.exit(1)
    response = response.text.split('\n')
    try:
        response.remove('')  # Remove empty element if any
    except ValueError:
        pass
    return response


def generate_random_name(list1, list2):
    adjectives = retrieve_list(list1)
    animals = retrieve_list(list2)
    return \
        random.choice(adjectives).lower().replace(',', '').replace(' ', '-') +\
        '-' + \
        random.choice(animals).lower().replace(',', '').replace(' ', '-')


def show_droplets(token, tag=None):
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets(tag_name=tag)
    for droplet in my_droplets:
        print('Droplet id:   {}'.format(droplet.id))
        print('Droplet name: {}'.format(droplet.name))
        print('Droplet ip:   {}'.format(droplet.ip_address))


def show_droplet(token, id):
    manager = digitalocean.Manager(token=token)
    droplet = manager.get_droplet(id)
    print('Droplet id:   {}'.format(droplet.id))
    print('Droplet name: {}'.format(droplet.name))
    print('Droplet ip:   {}'.format(droplet.ip_address))


def get_droplet(token, id):
    manager = digitalocean.Manager(token=token)
    droplet = manager.get_droplet(id)
    return droplet


def get_ssh_keys(token):
    manager = digitalocean.Manager(token=token)
    keys = manager.get_all_sshkeys()
    return keys


def detroy_droplets(token):
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        droplet.destroy()


def main():
    ANIMALS_LIST_URL = 'https://raw.githubusercontent.com/hzlzh/Domain-Name-List/master/Animal-words.txt'  # noqa
    ADJECTIVES_LIST_URL = 'https://raw.githubusercontent.com/gef756/namegen/master/adjectives.txt'  # noqa
    TAG = 'docker'
    REGION = 'fra1'  # Frankfurt
    IMAGE = 'ubuntu-16-04-x64'
    DROPLET_SIZE = 's-1vcpu-1gb'

    TOKEN = os.getenv('DIGITALOCEAN_TOKEN')
    if not TOKEN:
        print('Please set DIGITALOCEAN_TOKEN environment variable.')
        sys.exit(1)

    show_droplets(TOKEN, TAG)

    droplet = digitalocean.Droplet(token=TOKEN,
                                   name=generate_random_name(
                                       ADJECTIVES_LIST_URL,
                                       ANIMALS_LIST_URL),
                                   region=REGION,
                                   image=IMAGE,
                                   size_slug=DROPLET_SIZE,
                                   tags=[TAG],
                                   ssh_keys=get_ssh_keys(TOKEN))
    droplet.create()
    wait_completion(droplet)
    show_droplet(TOKEN, droplet.id)

    time.sleep(30)
    detroy_droplets(TOKEN)


if __name__ == "__main__":
    main()
