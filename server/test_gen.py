import sys
sys.path.append('.')
from app.utils.query_generator import generate_queries
print(generate_queries("Capital One", "test", 5))
