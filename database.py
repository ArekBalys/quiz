from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Database(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    best_score = db.Column(db.Integer, nullable=False, default=0)
    uwagi = db.Column(db.String(255), nullable=True)

    def as_dict(self):
        return {
            "name": self.name,
            "best_score": self.best_score,
            "uwagi": self.uwagi
        }
