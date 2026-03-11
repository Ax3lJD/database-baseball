from app import engine, Base
from app.models import WordleScore

# Create the wordle_scores table
Base.metadata.create_all(engine)
print("Wordle scores table created successfully!")