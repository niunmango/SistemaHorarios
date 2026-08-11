import os
from app import create_app, db
from app.seed import seed_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed database automatically if empty
        from app.models import Carrera
        if Carrera.query.count() == 0:
            seed_database()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
