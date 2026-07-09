# seed entire 4 source data order by one command (reproducible)
from generators import gen_crm, gen_stripe, seed_postgres, seed_mongo

def main() -> None:
    print("Seeding entire 4 sources")
    gen_crm.main()          # CRM -> CSV
    gen_stripe.main()       # Stripe -> JSON
    seed_postgres.main()    # App -> Postgres
    seed_mongo.main()       # Events -> Mongo
    print("Finish")

if __name__ == "__main__":
    main()