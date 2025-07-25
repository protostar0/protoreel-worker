import os
USE_SQL_DB = os.environ.get("USE_SQL_DB", "true").lower() == "true"

if USE_SQL_DB:
    print("[user_db] Using SQL DB (SQLAlchemy/PostgreSQL)")
    from datetime import datetime
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.evfdzesqvqwtcwxdiaar:Protovideo%402025@aws-0-eu-north-1.pooler.supabase.com:6543/postgres')
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base = declarative_base()

    retry_on_transient = retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((OperationalError, DBAPIError))
    )

    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, nullable=False)
        api_key = Column(String, unique=True, nullable=False)
        credits = Column(Integer, default=0, nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    class Task(Base):
        __tablename__ = 'tasks'
        id = Column(String, primary_key=True, index=True)  # UUID string
        user_api_key = Column(String, nullable=False, index=True)
        status = Column(String, nullable=False, default='queued')
        result = Column(JSON, nullable=True)
        error = Column(String, nullable=True)
        request_payload = Column(JSON, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def init_db():
        Base.metadata.create_all(bind=engine)

    def create_user(email: str, initial_credits: int = 10) -> str:
        import secrets
        api_key = secrets.token_hex(16)
        db = SessionLocal()
        try:
            user = User(email=email, api_key=api_key, credits=initial_credits)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.api_key
        except IntegrityError:
            db.rollback()
            raise ValueError('User with this email already exists')
        finally:
            db.close()

    def get_user_by_api_key(api_key: str):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if user:
                return {
                    'id': user.id,
                    'email': user.email,
                    'api_key': user.api_key,
                    'credits': user.credits,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat(),
                }
            return None
        finally:
            db.close()

    def update_credits(api_key: str, delta: int):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if user:
                user.credits += delta
                db.commit()
        finally:
            db.close()

    def create_or_update_test_user(credit: int = 10):
        api_key = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
        email = "test@example.com"
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if user:
                user.credits = credit
                user.is_active = True
            else:
                user = User(email=email, api_key=api_key, credits=credit, is_active=True)
                db.add(user)
            db.commit()
            return api_key
        finally:
            db.close()

    def create_task(task_id: str, user_api_key: str, request_payload: dict):
        db = SessionLocal()
        try:
            task = Task(
                id=task_id,
                user_api_key=user_api_key,
                status='queued',
                request_payload=request_payload,
            )
            db.add(task)
            db.commit()
            return task
        finally:
            db.close()

    @retry_on_transient
    def update_task_status(task_id: str, status: str, result: dict = None, error: str = None):
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            db.commit()
            return task
        finally:
            db.close()

    @retry_on_transient
    def get_task_by_id(task_id: str):
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            return task
        finally:
            db.close()
else:
    print("[user_db] Using in-memory DB for user/task storage (local test mode)")
    import secrets
    _users = {}
    _tasks = {}

    def create_user(email: str, initial_credits: int = 10) -> str:
        api_key = secrets.token_hex(16)
        _users[api_key] = {
            "id": len(_users) + 1,
            "email": email,
            "api_key": api_key,
            "credits": initial_credits,
            "is_active": True,
            "created_at": "localtest"
        }
        return api_key

    def get_user_by_api_key(api_key: str):
        return _users.get(api_key)

    def update_credits(api_key: str, delta: int):
        if api_key in _users:
            _users[api_key]["credits"] += delta

    def create_or_update_test_user(credit: int = 10):
        api_key = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
        email = "test@example.com"
        if api_key in _users:
            _users[api_key]["credits"] = credit
            _users[api_key]["is_active"] = True
        else:
            _users[api_key] = {
                "id": len(_users) + 1,
                "email": email,
                "api_key": api_key,
                "credits": credit,
                "is_active": True,
                "created_at": "localtest"
            }
        return api_key

    def create_task(task_id: str, user_api_key: str, request_payload: dict):
        _tasks[task_id] = {
            "id": task_id,
            "user_api_key": user_api_key,
            "status": "queued",
            "result": None,
            "error": None,
            "request_payload": request_payload,
        }
        return _tasks[task_id]

    def update_task_status(task_id: str, status: str, result: dict = None, error: str = None):
        if task_id in _tasks:
            _tasks[task_id]["status"] = status
            if result is not None:
                _tasks[task_id]["result"] = result
            if error is not None:
                _tasks[task_id]["error"] = error
            return _tasks[task_id]
        return None

    def get_task_by_id(task_id: str):
        return _tasks.get(task_id) 