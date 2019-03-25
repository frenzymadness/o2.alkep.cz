# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from flask import Flask, request, render_template, redirect, url_for, flash
from collections import defaultdict, OrderedDict
from zipfile import ZipFile
from os import path
import xml.etree.ElementTree as ET
import json

app = Flask(__name__)
app.secret_key = 'super secret key'

root = path.dirname(path.abspath(__file__))


def new_person(name="???", group="???", types=None):
    person = {"name": name, "group": group, "sum": 0.0}
    for type in types:
        person[type] = 0.0

    return person


def load_persons():
    with open(path.join(root, "persons.json")) as persons_file:
        persons = json.load(persons_file)
        persons = OrderedDict(sorted(persons.items()))

    return persons


@app.template_filter("format_number")
def format_number(value):
    rounded = round(value, 2)
    string = str(rounded)
    return string.replace(".", ",")


@app.route("/", methods=["GET"])
def index():
    persons = load_persons()
    return render_template("index.html", persons=persons)


@app.route("/save_persons", methods=["POST"])
def save_persons():
    data = request.form["persons"]
    persons = {}
    try:
        for line in data.split("\n"):
            if "," not in line:
                continue
            name, group, phone = line.strip().split(",")
            persons[phone.strip()] = new_person(name.strip(), group.strip())
    except Exception:
        flash("CHYBA: Neplatný vstup - někde něco chybělo nebo bylo navíc",
              "danger")
        return redirect(url_for('index'))
    else:
        with open(path.join(root, "persons.json"), mode="w") as persons_file:
            json.dump(persons, persons_file)

    flash("OK: Nastavení uloženo!", "success")
    return redirect(url_for('index'))


@app.route("/process", methods=["POST"])
def process():
    persons = load_persons()
    try:
        file = request.files['input-file']
    except Exception:
        flash("CHYBA: Nebyl vložen soubor ke zpracování", "danger")
        return redirect(url_for("index"))

    if file.filename.endswith(".zip"):
        zip = ZipFile(file)
        xml = zip.open(file.filename[:-4])
        tree = ET.parse(xml)
    else:
        tree = ET.parse(file)

    to_process = [
        ("regular", "regularCharges", "rcTotalPriceWithVat"),
        ("usage", "usageCharges", "ucTotalPriceWithVat"),
        ("payments", "payments", "paymentTotalPrice"),
        ("one_time", "oneTimeCharges", "otcTotalPriceWithVat"),
        ("services", "additionalServices", "asTotalPriceWithVat"),
    ]

    types = [type for type, _, _ in to_process]

    # For loop to get data about every customer/phone number
    for customer in tree.findall(".//subscriber[@accountType='CUST']"):
        phone = customer.attrib["phoneNumber"]
        try:
            person = persons[phone]
        except KeyError:
            person = new_person(types=types)
            persons[phone] = person

        for type, tag, attrib in to_process:
            try:
                rc = customer.findall(".//" + tag)[0]
                person[type] += float(rc.attrib[attrib])
            except IndexError:
                pass

            person["sum"] += person[type]

    # Groups of customers
    groups = defaultdict(lambda: defaultdict(float))
    for phone, person in persons.items():
        group = person["group"]
        for type, _, _ in to_process:
            groups[group][type] += person[type]
            groups[group]["sum"] += person[type]

    groups = OrderedDict(sorted(groups.items()))

    # Summaries (last line of each table)
    sums = {}
    for type, _, _ in to_process:
        sums["persons_" + type] = sum([p[type] for _, p in persons.items()])
    sums["all_persons"] = sum([v for v in sums.values()])

    for type, _, _ in to_process:
        sums["group_" + type] = sum([g[type] for _, g in groups.items()])
    sums["all_groups"] = sum([v
                              for k, v in sums.items()
                              if k.startswith("group_")])

    return render_template("index.html", persons=persons, groups=groups,
                           sums=sums)


if __name__ == '__main__':
    app.run(debug=True)
