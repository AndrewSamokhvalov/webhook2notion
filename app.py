import copy
import csv
import datetime
import os
import re
import time
from threading import Thread

from flask import Flask
from notion.client import NotionClient

status_labels = {
    "pending": "pending",
    "p": "pending",
    "dnhtua": "don't know how to use atm",
    "iftd": "if nothing to do",
    "if nothing to do": "if nothing to do",
    "completed": "completed",
    "c": "completed",
    "unprocessed": "unprocessed",
    "u": "unprocessed",
    "wbnif": "will be needed in future",
    "will be needed in future": "will be needed in future",
    "current focus": "current focus",
    "cf": "current focus",
}

tags_relationships = {
    "o1 visa": ["living"],
    "robotics": ["interests"],
    "biology": ["interests"],
    "startups": ["interests"],
    "ai": ["interests"],
    "bitcoin": ["interests"],
    "sleep": ["health"],
    "behaviour": ["health"],
    "automation": ["foundation"],
    "mental models": ["thinking", "learning"],
    "weird things to do": ["other"]
}


def add_related_tags(tags):
    ctags = tags
    tags = []
    for tag in ctags:
        tags.append(tag)

        try:
            related_tag = tag
            while True:
                related_tags = tags_relationships[related_tag]
                for related_tag in related_tags:
                    tags.append(related_tag)

        except KeyError:
            pass

    return tags


def import_from_instapaper(cv):
    path = "/Users/andrey/Downloads/instapaper-export.csv"

    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        i = 0

        for row in reader:
            if i < 271:
                i += 1
                continue

            state = extract_instapaper_tags(row["Folder"])
            if state is None:
                continue

            tags = add_related_tags(state["tags"])

            crow = cv.collection.add_row()
            crow.title = row["Title"]
            crow.set_property("Tags", tags)
            crow.set_property("Status", state["status"])
            crow.set_property("Url", row["URL"])
            crow.set_property("Created", datetime.datetime.utcfromtimestamp(
                int(row["Timestamp"])))

            i += 1
            print(i)


def extract_instapaper_tags(folder):
    pending_sign = b"\xe2\x8c\x9b"
    complete_sign = b"(+)"
    status = "pending"

    folder = folder.encode("utf-8")
    if len(folder) == 0:
        return None

    if folder[:3] == pending_sign:
        folder = folder.replace(pending_sign, b"")
        status = "pending"
    elif folder[:3] == complete_sign:
        folder = folder.replace(complete_sign, b"")
        status = "completed"

    folder = folder.decode()

    folder = str.lower(folder)
    tags = folder.split(",")

    ctags = tags
    tags = []
    for tag in ctags:
        tag = tag.lstrip()
        tags.append(tag)

    tags = transform_instapaper_tags(tags)
    if tags is None:
        return None

    return {
        "tags": tags,
        "status": status,
    }


def transform_instapaper_tags(tags):
    tags = copy.deepcopy(tags)

    ctags = tags
    tags = []

    for tag in ctags:
        if tag == "bmi":
            tags.append("biology")
            tags.append("engineering")

        elif tag == "moscow events":
            tags.append("moscow")
            tags.append("events")

        elif tag == "boston meetings":
            tags.append("boston")
            tags.append("events")
        elif tag == "unread":
            pass
        elif tag == "weird thing to do":
            tags.append("weird things to do")
        elif tag == "gatherings":
            tags.append("events")
        elif tag == "archive":
            return None
        else:
            tags.append(tag)

    return tags


def automatic_remove():
    # after 5 month of last edit
    pass


def extract_state(title):
    if len(title) == 0:
        return None
    
    if title[0] != "[":
        return None

    matches = re.findall("\[([\w+,*\s*]+)\]", title)

    if len(matches) == 0:
        return None

    tags_string = matches[0]
    tags_string.replace(" ", "")
    tags = tags_string.split(",")

    ctags = tags
    tags = []
    status = "unprocessed"
    for tag in ctags:
        tag = tag.lstrip()
        if tag in status_labels:
            status = status_labels[tag]
        else:
            tags.append(tag)

    tags = add_related_tags(tags)

    k = 0
    for i, l in zip(range(0, len(title)), title):
        if l == "]":
            k = i + 1
            break

    return {
        "tags": tags,
        "status": status,
        "title": title[k:].lstrip()
    }


row_cache = {}


def automatic_article_check(cv):
    for row in cv.collection.get_rows():
        if row.id in row_cache:
            continue

        row_cache[row.id] = None

        state = extract_state(row.title)
        if state is None:
            continue

        row.title = state["title"]
        row.set_property("Tags", state["tags"])
        row.set_property("Status", state["status"])
        print("Title: %s, Tags: %s, Status: %s" % (state["title"],
                                                   state["tags"],
                                                   state["status"]))


def check_notion_table():
    # Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so
    client = NotionClient(token_v2=os.environ.get("TOKEN"))

    cv = client.get_collection_view(
        "https://www.notion.so/andrewshvv/2fc0a52342b64f91b19c911f4e7b898d?v=8e1b80f383e94d21b0835f880976578a")

    while True:
        time.sleep(10)
        print("exec automatic_article_check()")
        automatic_article_check(cv)


app = Flask(__name__)


@app.route('/', methods=['GET'])
def main_handler():
    # fuck you heroku
    pass


if __name__ == '__main__':
    app.debug = True

    t = Thread(target=check_notion_table)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
