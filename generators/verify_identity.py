# demonstrate one person will appear in entire 4 source with 4 difference keys
from __future__ import annotations
import csv, json, os
import psycopg
from pymongo import MongoClient
from dotenv import load_dotenv
from generators.identities import build_persons, DATA_DIR

load_dotenv()

def load_source_keys():
    # CRM with clean email
    with (DATA_DIR / "crm" / "contacts.csv").open(encoding="utf-8") as file:
        crm = {read["contact_email"].strip().lower() for read in csv.DictReader(file)}

    # Stripe with customer_id
    stripe = {customer["id"] for customer in json.load((DATA_DIR / "stripe" / "customers.json").open())}

    # App with user id
    with psycopg.connect(host="localhost", port=5434,
                         dbname=os.environ["APP_PG_DB"],
                         user=os.environ["APP_PG_USER"],
                         password=os.environ["APP_PG_PASSWORD"]) as conn:
        app = {read[0] for read in conn.execute("SELECT user_id FROM app.users")}

    # Mongo with anonymous_id
    with MongoClient(host="localhost", port=27017,
                     username=os.environ["MONGO_USER"],
                     password=os.environ["MONGO_PASSWORD"],
                     authSource="admin") as client:
        mongo = set(client["events_db"]["events"].distinct("anonymous_id"))

    return crm, stripe, app, mongo

def main() -> None:
    crm, stripe, app, mongo = load_source_keys()
    persons = build_persons()

    def in_all(person) -> bool:
        return (person.email in crm and person.stripe_customer_id in stripe and
                person.app_user_id in app and person.event_anonymous_id in mongo)

    for person in persons: # find the first person have entire 4 sources
        if in_all(person):
            print(f"The same person entire 4 source - {person.person_id}")
            print(f"\t{person.first_name} - {person.last_name}")
            break

    amount = sum(in_all(person) for person in persons)
    print(f"Amount of people have entire 4 sources: {amount}")

if __name__ == "__main__":
    main()