\# TaskVault

TaskVault is a secure, role-based task management backend built using Django REST Framework.
It provides structured task workflows, role-based access control, immutable task history, and collaborative comments.

The project follows clean architecture principles and is suitable for both individual task management and team-oriented workflows.

---

## Features

- JWT-based authentication and authorization
- Role-based access control (Admin and User)
- Task creation, assignment, and lifecycle management
- Immutable task history for status and priority changes
- Comment system for task collaboration
- Soft delete strategy for users, tasks, and comments
- UUID-based primary keys
- Centralized permission handling
- API-first design

---

## Tech Stack

- Python 3.12+
- Django
- Django REST Framework
- PostgreSQL
- JWT (SimpleJWT)
- Docker

---

## Project Structure

```bash
taskvault/
├── core/ # Shared utilities, permissions, pagination
├── users/ # User authentication and management
├── tasks/ # Task, comments, and history modules
├── taskvault/ # Project configuration
├── scripts/ # Utility and seed scripts
├── manage.py
├── requirements.txt
└── .env
```



---

## Getting Started

### Prerequisites

- Python 3.12 or higher
- PostgreSQL
- Docker (optional but recommended)

---

### Environment Setup

Create a `.env` file in the project root:
DEBUG=True
SECRET_KEY=your-secret-key

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

ACCESS_TOKEN_LIFETIME=
REFRESH_TOKEN_LIFETIME=



---

### Local Setup (Without Docker)

```bash
git clone https://github.com/your-username/taskvault.git
cd taskvault

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

docker-compose up --build

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
