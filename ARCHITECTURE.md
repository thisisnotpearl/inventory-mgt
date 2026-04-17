# Architecture

## Overview
A RESTful Inventory Management System built with Django REST 
Framework and MongoDB via MongoEngine. The system follows 
hexagonal (ports & adapters) architecture to keep business 
logic independent of HTTP and database concerns.

## Layer structure

HTTP Request
    ↓
controllers/        → receives HTTP, calls service, returns JSON
    ↓
services/           → all business logic and validation lives here
    ↓
repositories/       → all MongoDB reads and writes live here
    ↓
models/             → MongoEngine document schema definitions
    ↓
MongoDB


### controllers/
- Owns: parsing request, calling service, returning JsonResponse
- Must not: contain any business logic or query MongoDB directly
- Example: product_controller.py

### services/
- Owns: validation rules, business decisions, orchestration
- Must not: know anything about HTTP or MongoDB queries
- Example: product_service.py

### repositories/
- Owns: all MongoEngine queries (save, find, delete)
- Must not: contain business logic
- Example: product_repository.py

### models/
- Owns: MongoEngine Document class + field definitions
- Must not: contain business logic methods
- Example: product.py


## Project structure

interneers-invmgt/
├── inventory-project/
│   ├── config/             → Django settings, urls, wsgi, db.py
│   ├── products/           → product domain (controllers, services, repositories, models)
│   ├── categories/         → category domain (same structure)
│   └── manage.py
├── docker-compose.yml      → runs MongoDB locally
├── requirements.txt
├── .env                    → secrets, never committed
└── .env.example            → template for env variables


## Design decisions

### Why hexagonal architecture?
Problem: if views talk directly to MongoDB, you can't test 
business logic without a real database running.

Decision: strict layers where service layer has zero knowledge 
of HTTP or MongoDB. Controllers depend on services, services 
depend on repository interfaces.

Trade-off: more files and folders than a standard Django project. 
Worth it because every service method can be unit tested by 
mocking the repository.

### Why MongoDB over Django's default SQLite/Postgres?
Problem: product attributes vary — electronics have voltage 
specs, food items have expiry dates. A fixed SQL schema 
requires constant migrations for new fields.

Decision: MongoDB's flexible documents let each product carry 
only the fields it needs without schema migrations.

Trade-off: no Django ORM, no makemigrations. MongoEngine 
replaces the ORM but has less community support than Django ORM.

### Why soft deletes?
Problem: hard-deleting a product loses its stock history 
and breaks any audit references pointing to that ID.

Decision: products get is_deleted=True + deleted_at timestamp. 
All queries filter on is_deleted=False automatically in the 
repository layer.

Trade-off: deleted products stay in the collection forever. 
In production, old deleted records would be archived after 
some months.


## What I'd do differently in production
