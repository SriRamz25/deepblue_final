import os
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:sentra_secure_2026@localhost:5432/fraud_detection')
os.environ.setdefault('REDIS_URL','redis://localhost')
os.environ.setdefault('SECRET_KEY','dev')
from app.config import settings
p = settings.ML_MODEL_PATH
print('configured ML_MODEL_PATH:', p)
print('cwd:', os.getcwd())
print('exists?', os.path.exists(p))
print('abs:', os.path.abspath(p))
expected = os.path.abspath(os.path.join(os.getcwd(), '..', 'ML', 'fraud_model.cbm'))
print('expected exists?', os.path.exists(expected), expected)
