"""
scripts/seed_users.py
========================
Creates a login for every existing mentor and intern, plus one admin
account. Uses each person's existing email as their login email, and
generates a simple default password (their name + intern/mentor id)
so credentials are predictable for a demo — NOT meant for real
production use.

Run once, after applying auth_migration.sql:
    python -m scripts.seed_users

Writes generated credentials to seeded_credentials.csv so you can
hand out logins for the demo without hunting through the DB.
"""
import csv
import re

from passlib.context import CryptContext

from app.database import SessionLocal
from app.models.db_models import User, Mentor, Intern

ADMIN_EMAIL = "admin@ezitech.com"
ADMIN_PASSWORD = "Admin@123"  # change this before any real deployment

# Lower rounds (default is 12) — this is a demo seed script hashing
# hundreds of rows, not a production login path. Still safe enough
# for a class project; drastically faster.
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=8)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main():
    db = SessionLocal()
    created = []

    # --- Admin ---
    if not db.query(User).filter(User.email == ADMIN_EMAIL).first():
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        created.append(("admin", ADMIN_EMAIL, ADMIN_PASSWORD, "Admin"))
        print("Created admin account.")

    # --- Mentors ---
    mentors = db.query(Mentor).all()
    print(f"Seeding {len(mentors)} mentors...")
    for idx, m in enumerate(mentors, start=1):
        if not m.email:
            print(f"  [{idx}/{len(mentors)}] skipping mentor {m.mentor_id} ({m.name}) — no email")
            continue
        if db.query(User).filter(User.email == m.email).first():
            continue
        password = f"{slugify(m.name)}{m.mentor_id}"
        user = User(
            email=m.email,
            password_hash=hash_password(password),
            role="mentor",
            mentor_id=m.mentor_id,
        )
        db.add(user)
        created.append(("mentor", m.email, password, m.name))
        if idx % 5 == 0 or idx == len(mentors):
            print(f"  [{idx}/{len(mentors)}] mentors done")

    # --- Interns ---
    interns = db.query(Intern).all()
    print(f"Seeding {len(interns)} interns... (this is the slow part, be patient)")
    for idx, i in enumerate(interns, start=1):
        if not i.email:
            print(f"  [{idx}/{len(interns)}] skipping intern {i.intern_id} ({i.name}) — no email")
            continue
        if db.query(User).filter(User.email == i.email).first():
            continue
        password = f"{slugify(i.name)}{i.intern_id}"
        user = User(
            email=i.email,
            password_hash=hash_password(password),
            role="student",
            intern_id=i.intern_id,
        )
        db.add(user)
        created.append(("student", i.email, password, i.name))
        if idx % 50 == 0 or idx == len(interns):
            print(f"  [{idx}/{len(interns)}] interns done")

    db.commit()
    db.close()

    with open("seeded_credentials.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["role", "email", "password", "name"])
        writer.writerows(created)

    print(f"\nDone. Created {len(created)} user accounts.")
    print("Credentials written to seeded_credentials.csv — keep this out of git.")


if __name__ == "__main__":
    main()