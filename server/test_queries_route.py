import sys
sys.path.append('.')
from app import create_app
from app.models import db, Company, User
import json

app = create_app()

with app.app_context():
    # Attempt to mock what user sees
    db.create_all()
    c = Company.query.filter_by(name="Ebay").first()
    if not c:
        c = Company(name="Ebay", primary_domain="ebay.com")
        db.session.add(c)
        db.session.commit()
        
    u = User.query.filter_by(email="test@example.com").first()
    if not u:
        u = User(email="test@example.com", company_id=c.id)
        db.session.add(u)
        db.session.commit()

    from app.routes.queries import generate_queries
    try:
        generated = generate_queries(company_name=c.name, product="test", num_queries=5)
        print("Generated:")
        for g in generated:
            print(f"- {g.text}")
    except Exception as e:
        print("Exception:", e)

