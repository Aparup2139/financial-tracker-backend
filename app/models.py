from app import db, bcrypt
from datetime import datetime
import enum

class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

class User(db.Model):
    # ... (The User model remains the same as before)
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    transactions = db.relationship('Transaction', backref='owner', lazy=True, cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='owner', lazy=True, cascade="all, delete-orphan")

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Make sure a user cannot have two categories with the same name
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='_user_category_uc'),)

    def __repr__(self):
        return f'<Category {self.name}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False) # Always store amount as a positive value
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.Enum(TransactionType), nullable=False, default=TransactionType.EXPENSE)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    category = db.relationship('Category', backref='transactions')

    def to_dict(self):
        # The frontend expects a negative amount for expenses, so we adjust it here
        display_amount = -self.amount if self.type == TransactionType.EXPENSE else self.amount
        
        return {
            'id': self.id,
            'description': self.description,
            'amount': display_amount, # This now matches your frontend's logic
            'date': self.date.isoformat(),
            'type': self.type.value,
            'category': self.category.name, # Directly include the category name
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Transaction {self.description}>'