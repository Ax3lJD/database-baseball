from app import engine, Base
from app.models import ConnectionsScore, StrandsScore

Base.metadata.create_all(engine)
print("New game tables created successfully!")