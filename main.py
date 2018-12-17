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


def new_person(name="???", group="???"):
    return {
        "name": name,
        "group": group,
        "usage": 0.0,
        "regular": 0.0,
        "one_time": 0.0,
        "payments": 0.0
    }


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

    for customer in tree.findall(".//subscriber[@accountType='CUST']"):
        phone = customer.attrib["phoneNumber"]
        try:
            person = persons[phone]
        except KeyError:
            person = new_person()
            persons[phone] = person
        try:
            rc = customer.findall(".//regularCharges")[0]
            person["regular"] += float(rc.attrib["rcTotalPriceWithVat"])
        except IndexError:
            pass
        try:
            uc = customer.findall(".//usageCharges")[0]
            person["usage"] += float(uc.attrib["ucTotalPriceWithVat"])
        except IndexError:
            pass
        try:
            pay = customer.findall(".//payments")[0]
            person["payments"] += float(pay.attrib["paymentTotalPrice"])
        except IndexError:
            pass
        try:
            one_time = customer.findall(".//oneTimeCharges")[0]
            person["one_time"] += float(one_time.attrib["otcTotalPriceWithVat"])
        except IndexError:
            pass

        person["sum"] = sum([person["regular"],
                             person["usage"],
                             person["payments"],
                             person["one_time"]])

    groups = defaultdict(lambda: defaultdict(float))
    for phone, person in persons.items():
        group = person["group"]
        groups[group]["usage"] += person["usage"]
        groups[group]["regular"] += person["regular"]
        groups[group]["payments"] += person["payments"]
        groups[group]["one_time"] += person["one_time"]

        groups[group]["sum"] += sum([person["regular"],
                                     person["usage"],
                                     person["payments"],
                                     person["one_time"]])

    groups = OrderedDict(sorted(groups.items()))

    # Summaries (last line of each table)
    sums = {}
    sums["persons_regular"] = sum([p["regular"] for _, p in persons.items()])
    sums["persons_usage"] = sum([p["usage"] for _, p in persons.items()])
    sums["persons_payments"] = sum([p["payments"] for _, p in persons.items()])
    sums["persons_one_time"] = sum([p["one_time"] for _, p in persons.items()])
    sums["all_persons"] = sum([v for v in sums.values()])

    sums["group_regular"] = sum([g["regular"] for _, g  in groups.items()])
    sums["group_usage"] = sum([g["usage"] for _, g  in groups.items()])
    sums["group_payments"] = sum([g["payments"] for _, g  in groups.items()])
    sums["group_one_time"] = sum([g["one_time"] for _, g  in groups.items()])
    sums["all_groups"] = sum([v
                              for k, v in sums.items()
                              if k.startswith("group_")])

    return render_template("index.html", persons=persons, groups=groups,
                           sums=sums)


if __name__ == '__main__':
    app.run(debug=True)
