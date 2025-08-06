from flask import request, jsonify, Blueprint
from .models import db, User, Transaction, TransactionType, Category
from . import bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy import func, extract
from datetime import datetime, timedelta

main_bp = Blueprint('main_bp', __name__)
@main_bp.route('/')
def index():
    return "Welcome to the Financial Tracker API!"
# --- Helper Functions ---
def get_or_create_category(name, user_id):
    """Gets a category by name for a user, or creates it if it doesn't exist."""
    category = Category.query.filter_by(name=name, user_id=user_id).first()
    if not category:
        category = Category(name=name, user_id=user_id)
        db.session.add(category)
        # We don't commit here; let the calling function handle the commit.
    return category

def create_default_categories(user_id):
    """Creates a default set of categories for a new user."""
    # Based on your TransactionList.jsx and ExpenseChart.jsx
    default_categories = ['Food', 'Travel', 'Shopping', 'Entertainment', 'Income', 'Other']
    for cat_name in default_categories:
        category = Category(name=cat_name, user_id=user_id)
        db.session.add(category)
    db.session.commit()

# --- Authentication Routes ---

@main_bp.route('/register', methods=['POST'])
def register():
    # ... (register logic is mostly the same)
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('username'):
        return jsonify({"msg": "Missing username, email, or password"}), 400

    if User.query.filter_by(email=data['email']).first() or User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Email or username already exists"}), 409

    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.flush() # Flush to get the new_user.id for category creation
    create_default_categories(new_user.id) # Create categories for the new user

    return jsonify({"msg": "User created successfully"}), 201

@main_bp.route('/login', methods=['POST'])
def login():
    # ... (login logic is unchanged)
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token)
    return jsonify({"msg": "Bad email or password"}), 401

# --- Main Dashboard and Transaction Routes ---

@main_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    user_id = get_jwt_identity()
    
    # -- 1. STATS CALCULATION (for DashboardStats.jsx) --
    now = datetime.utcnow()
    # This month's data
    this_month_income = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id==user_id, Transaction.type==TransactionType.INCOME, extract('month', Transaction.date)==now.month, extract('year', Transaction.date)==now.year).scalar() or 0
    this_month_expenses = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id==user_id, Transaction.type==TransactionType.EXPENSE, extract('month', Transaction.date)==now.month, extract('year', Transaction.date)==now.year).scalar() or 0
    
    # Last month's data for comparison
    last_month_date = now - timedelta(days=now.day) # Go to the last day of the previous month
    last_month_income = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id==user_id, Transaction.type==TransactionType.INCOME, extract('month', Transaction.date)==last_month_date.month, extract('year', Transaction.date)==last_month_date.year).scalar() or 0
    last_month_expenses = db.session.query(func.sum(Transaction.amount)).filter(Transaction.user_id==user_id, Transaction.type==TransactionType.EXPENSE, extract('month', Transaction.date)==last_month_date.month, extract('year', Transaction.date)==last_month_date.year).scalar() or 0

    total_balance = this_month_income - this_month_expenses
    savings_rate = (total_balance / this_month_income * 100) if this_month_income > 0 else 0

    def get_change_percent(current, previous):
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100

    stats = {
        "total_balance": total_balance,
        "total_income": this_month_income,
        "total_expenses": this_month_expenses,
        "savings_rate": savings_rate,
        "balance_change": get_change_percent(total_balance, last_month_income - last_month_expenses),
        "income_change": get_change_percent(this_month_income, last_month_income),
        "expense_change": get_change_percent(this_month_expenses, last_month_expenses)
    }

    # -- 2. EXPENSE BREAKDOWN (for ExpenseChart.jsx) --
    expense_breakdown = db.session.query(Category.name, func.sum(Transaction.amount).label('value')).join(Transaction).filter(Transaction.user_id==user_id, Transaction.type==TransactionType.EXPENSE, extract('month', Transaction.date)==now.month, extract('year', Transaction.date)==now.year).group_by(Category.name).all()
    expense_breakdown_dict = [{"name": name, "value": value} for name, value in expense_breakdown]

    # -- 3. RECENT TRANSACTIONS (for TransactionList.jsx) --
    recent_transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).limit(10).all()
    
    return jsonify({
        "stats": stats,
        "expense_breakdown": expense_breakdown_dict,
        "recent_transactions": [t.to_dict() for t in recent_transactions]
    })


@main_bp.route('/transactions', methods=['POST'])
@jwt_required()
def add_transaction():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Validate input data
    required_fields = ['description', 'amount', 'type', 'category', 'date']
    if not all(field in data for field in required_fields):
        return jsonify({"msg": "Missing required fields"}), 400

    # Handle category
    category = get_or_create_category(data['category'], user_id)
    
    try:
        trans_type = TransactionType(data['type'])
        # Amount from frontend for expense is negative, we store positive
        amount = abs(float(data['amount']))
        date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid data format for type, amount, or date"}), 400
    
    new_transaction = Transaction(
        description=data['description'],
        amount=amount,
        type=trans_type,
        date=date,
        user_id=user_id,
        category=category # Assign the category object
    )

    db.session.add(new_transaction)
    db.session.commit()

    return jsonify(new_transaction.to_dict()), 201