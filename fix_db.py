from app import create_app
from models import db

app = create_app()

with app.app_context():
    print("Fixing database...")
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    
    # Drop tables in order of dependency (child first)
    tables_to_drop = ['applications', 'cart_items', 'order_items', 'registrations', 'carts', 'orders', 'products', 'users', 'students', 'events']
    
    for table in tables_to_drop:
        if table in tables:
            print(f"Dropping {table}...")
            db.session.execute(db.text(f"DROP TABLE {table}"))
            
    db.session.commit()
    
    print("Creating new tables...")
    db.create_all()
    print("Database fixed.")
