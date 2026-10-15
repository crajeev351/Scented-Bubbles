import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.products import Product

def run_migration():
    app = create_app()
    with app.app_context():
        products = Product.query.all()
        print(f"Total products to update: {len(products)}")
        updated_count = 0
        for p in products:
            current_name = (p.name or "").strip()
            if not current_name.lower().endswith("inspired perfume"):
                p.name = f"{current_name} Inspired Perfume"
                updated_count += 1
            
            p.inspired_by = None

        db.session.commit()
        print(f"Successfully updated {updated_count} product names and cleared inspired_by for all {len(products)} products.")

        # Print sample updated products
        sample = Product.query.limit(5).all()
        for s in sample:
            print(f"ID {s.id}: name='{s.name}', inspired_by={s.inspired_by}")

if __name__ == "__main__":
    run_migration()
