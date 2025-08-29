import os
USE_SQL_DB = os.environ.get("USE_SQL_DB", "true").lower() == "true"

if USE_SQL_DB:
    print("[user_db] Using SQL DB (SQLAlchemy/PostgreSQL)")
    from datetime import datetime
    from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON, func
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.exc import IntegrityError

    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.evfdzesqvqwtcwxdiaar:Protovideo%402025@aws-0-eu-north-1.pooler.supabase.com:6543/postgres')
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base = declarative_base()

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    class User(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, nullable=False)
        name = Column(String, nullable=True)
        picture = Column(String, nullable=True)
        locale = Column(String, nullable=True)
        country = Column(String, nullable=True)
        password_hash = Column(String, nullable=False)
        is_verified = Column(Boolean, default=False, nullable=False)
        api_key = Column(String, unique=True, nullable=False)
        credits = Column(Integer, default=0, nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        is_admin = Column(Boolean, default=False, nullable=False)
        google_signin = Column(Boolean, default=False, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    class Task(Base):
        __tablename__ = 'tasks'
        id = Column(String, primary_key=True, index=True)  # UUID string
        user_api_key = Column(String, nullable=False, index=True)
        status = Column(String, nullable=False, default='queued')
        result = Column(JSON, nullable=True)
        error = Column(String, nullable=True)
        request_payload = Column(JSON, nullable=True)
        log_uri = Column(String, nullable=True)  # New: Cloud Run Job logUri
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
        started_at = Column(DateTime, nullable=True)
        finished_at = Column(DateTime, nullable=True)

    class Payment(Base):
        __tablename__ = 'payments'
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, nullable=False, index=True)
        email = Column(String, nullable=False)
        amount = Column(Integer, nullable=False)  # in cents
        credits = Column(Integer, nullable=False)
        stripe_session_id = Column(String, nullable=False, unique=True)
        status = Column(String, nullable=False, default='succeeded')
        payment_metadata = Column(JSON, nullable=True)  # For storing subscription plan info
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    class UserMedia(Base):
        __tablename__ = 'user_media'
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, nullable=False, index=True)
        url = Column(String, nullable=False)
        type = Column(String, nullable=False)  # 'image', 'video', 'music', 'voice'
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    class AuditLog(Base):
        __tablename__ = 'audit_log'
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, nullable=True, index=True)
        admin_id = Column(Integer, nullable=True, index=True)
        action = Column(String, nullable=False)
        details = Column(String, nullable=True)
        ip = Column(String, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    class PlatformSettings(Base):
        __tablename__ = 'platform_settings'
        id = Column(Integer, primary_key=True)
        platform_name = Column(String, default='ProtoReel', nullable=False)
        maintenance_mode = Column(Boolean, default=False, nullable=False)
        registration_enabled = Column(Boolean, default=True, nullable=False)
        email_verification_required = Column(Boolean, default=True, nullable=False)
        max_credits_per_user = Column(Integer, default=1000, nullable=False)
        default_credits_new_user = Column(Integer, default=0, nullable=False)

    class Audio(Base):
        __tablename__ = 'audio'
        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, nullable=False, index=True)
        name = Column(String, nullable=False)
        description = Column(String, nullable=True)
        audio_url = Column(String, nullable=False)
        duration = Column(Integer, nullable=True)  # duration in seconds
        file_size = Column(Integer, nullable=True)  # file size in bytes
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def init_db():
        Base.metadata.create_all(bind=engine)

    def create_user(email: str, initial_credits: int = 0) -> str:
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

    def create_or_update_test_user(credit: int = 0):
        api_key = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
        email = "test@example.com"
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if user:
                user.credits = credit
                user.is_active = True
            else:
                user = User(email=email, api_key=api_key, credits=credit, is_active=True, password_hash="test")
                db.add(user)
            db.commit()
            return api_key
        finally:
            db.close()

    def create_task(task_id: str, user_api_key: str, request_payload: dict, log_uri: str = None):
        db = SessionLocal()
        try:
            task = Task(
                id=task_id,
                user_api_key=user_api_key,
                status='queued',
                request_payload=request_payload,
                log_uri=log_uri
            )
            db.add(task)
            db.commit()
            return task
        finally:
            db.close()

    def update_task_status(task_id: str, status: str, result: dict = None, error: str = None, log_uri: str = None):
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
            if log_uri is not None:
                task.log_uri = log_uri
            
            # Set timestamps based on status
            if status == 'inprogress' and task.started_at is None:
                task.started_at = datetime.utcnow()
            elif status in ['finished', 'failed'] and task.finished_at is None:
                task.finished_at = datetime.utcnow()
            
            db.commit()
            return task
        finally:
            db.close()

    def get_task_by_id(task_id: str):
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            return task
        finally:
            db.close()

    # Credit management functions for new system
    def get_user_active_tasks_credits(api_key: str):
        """Get total credits needed for user's current active tasks (queued + inprogress)"""
        db = SessionLocal()
        try:
            active_tasks = db.query(Task).filter(
                Task.user_api_key == api_key,
                Task.status.in_(['queued', 'inprogress'])
            ).all()
            total_credits_needed = 0
            for task in active_tasks:
                if task.request_payload and 'scenes' in task.request_payload:
                    # Calculate credits based on scene types
                    scenes = task.request_payload['scenes']
                    for scene in scenes:
                        if scene.get('type') == 'video':
                            if scene.get('prompt_video'):
                                total_credits_needed += 5  # AI video generation
                            elif scene.get('video_url'):
                                total_credits_needed += 1  # Existing video
                            else:
                                total_credits_needed += 1  # Default video scene
                        else:
                            total_credits_needed += 1  # Image scenes
            return total_credits_needed
        finally:
            db.close()

    def can_user_create_task(api_key: str, new_task_scenes: list):
        """Check if user has enough credits for new task + existing active tasks"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if not user:
                return False, "User not found"
            
            # Calculate credits needed for new task
            new_task_credits = 0
            for scene in new_task_scenes:
                if scene.get('type') == 'video':
                    if scene.get('prompt_video'):
                        new_task_credits += 5  # AI video generation
                    elif scene.get('video_url'):
                        new_task_credits += 1  # Existing video
                    else:
                        new_task_credits += 1  # Default video scene
                else:
                    new_task_credits += 1  # Image scenes
            
            # Get credits needed for existing active tasks
            active_tasks_credits = get_user_active_tasks_credits(api_key)
            total_credits_needed = active_tasks_credits + new_task_credits
            
            if user.credits >= total_credits_needed:
                return True, f"Sufficient credits. Available: {user.credits}, Needed: {total_credits_needed} (Active tasks: {active_tasks_credits}, New task: {new_task_credits})"
            else:
                return False, f"Insufficient credits. Available: {user.credits}, Needed: {total_credits_needed} (Active tasks: {active_tasks_credits}, New task: {new_task_credits})"
        finally:
            db.close()

    def get_user_task_summary(api_key: str):
        """Get detailed summary of user's active tasks and credit usage"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if not user:
                return None
            
            active_tasks = db.query(Task).filter(
                Task.user_api_key == api_key,
                Task.status.in_(['queued', 'inprogress'])
            ).all()
            
            task_details = []
            total_credits_reserved = 0
            
            for task in active_tasks:
                if task.request_payload and 'scenes' in task.request_payload:
                    scenes = task.request_payload['scenes']
                    task_credits = 0
                    scene_details = []
                    
                    for i, scene in enumerate(scenes):
                        scene_type = scene.get('type', 'unknown')
                        if scene_type == 'video':
                            if scene.get('prompt_video'):
                                scene_credits = 5
                                scene_desc = f"AI video generation: '{scene.get('prompt_video', '')[:50]}...'"
                            elif scene.get('video_url'):
                                scene_credits = 1
                                scene_desc = f"Existing video: {scene.get('video_url', '')[:50]}..."
                            else:
                                scene_credits = 1
                                scene_desc = "Video scene (default)"
                        else:
                            scene_credits = 1
                            scene_desc = f"Image scene: '{scene.get('prompt_image', scene.get('image_url', 'Generated/Uploaded'))[:50]}..."
                    
                        task_credits += scene_credits
                        scene_details.append({
                            "scene_index": i,
                            "type": scene_type,
                            "credits": scene_credits,
                            "description": scene_desc
                        })
                
                total_credits_reserved += task_credits
                task_details.append({
                    "task_id": task.id,
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "total_credits": task_credits,
                    "scenes": scene_details
                })
            
            return {
                "user_email": user.email,
                "available_credits": user.credits,
                "total_credits_reserved": total_credits_reserved,
                "credits_remaining_after_tasks": user.credits - total_credits_reserved,
                "active_tasks_count": len(active_tasks),
                "active_tasks": task_details
            }
        finally:
            db.close()

    def log_audit(db, action, user_id=None, admin_id=None, details=None, ip=None):
        log = AuditLog(
            user_id=user_id,
            admin_id=admin_id,
            action=action,
            details=details,
            ip=ip
        )
        db.add(log)
        db.commit()

    # Audio management functions
    def create_audio(user_id: int, name: str, description: str, audio_url: str, duration: int = None, file_size: int = None):
        db = SessionLocal()
        try:
            audio = Audio(
                user_id=user_id,
                name=name,
                description=description,
                audio_url=audio_url,
                duration=duration,
                file_size=file_size
            )
            db.add(audio)
            db.commit()
            db.refresh(audio)
            return audio
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def get_user_audio(user_id: int, limit: int = 50, offset: int = 0):
        db = SessionLocal()
        try:
            audio_list = db.query(Audio).filter(
                Audio.user_id == user_id,
                Audio.is_active == True
            ).order_by(Audio.created_at.desc()).offset(offset).limit(limit).all()
            return audio_list
        finally:
            db.close()

    def get_audio_by_id(audio_id: int, user_id: int = None):
        db = SessionLocal()
        try:
            query = db.query(Audio).filter(Audio.id == audio_id)
            if user_id:
                query = query.filter(Audio.user_id == user_id)
            audio = query.first()
            return audio
        finally:
            db.close()

    def update_audio(audio_id: int, user_id: int, name: str = None, description: str = None, audio_url: str = None):
        db = SessionLocal()
        try:
            print(f"[DEBUG] update_audio: audio_id={audio_id}, user_id={user_id}")
            print(f"[DEBUG] update_audio: name={name}, description={description}, audio_url={audio_url}")
            audio = db.query(Audio).filter(Audio.id == audio_id, Audio.user_id == user_id).first()
            if not audio:
                print(f"[DEBUG] update_audio: Audio not found")
                return None
            print(f"[DEBUG] update_audio: Found audio {audio.id}")
            if name:
                print(f"[DEBUG] update_audio: Updating name to {name}")
                audio.name = name
            if description is not None:
                print(f"[DEBUG] update_audio: Updating description to {description}")
                audio.description = description
            if audio_url:
                print(f"[DEBUG] update_audio: Updating audio_url to {audio_url}")
                audio.audio_url = audio_url
            print(f"[DEBUG] update_audio: Committing changes")
            db.commit()
            print(f"[DEBUG] update_audio: Successfully updated")
            # Copy attributes to dict before closing session
            audio_dict = {
                'id': audio.id,
                'name': audio.name,
                'description': audio.description,
                'audio_url': audio.audio_url,
                'duration': audio.duration,
                'file_size': audio.file_size,
                'created_at': audio.created_at,
                'updated_at': audio.updated_at
            }
            return audio_dict
        except Exception as e:
            print(f"[DEBUG] update_audio: Exception occurred: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    def delete_audio(audio_id: int, user_id: int):
        db = SessionLocal()
        try:
            audio = db.query(Audio).filter(Audio.id == audio_id, Audio.user_id == user_id).first()
            if not audio:
                return False
            
            # Delete from R2 if audio_url exists
            if audio.audio_url:
                try:
                    import boto3
                    from urllib.parse import urlparse
                    s3 = boto3.client(
                        "s3",
                        endpoint_url=os.environ.get("R2_ENDPOINT_URL"),
                        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
                    )
                    bucket = os.environ.get("R2_BUCKET_NAME", "upload-from-user")
                    
                    # Extract filename from URL
                    path = urlparse(audio.audio_url).path
                    filename = path.lstrip("/")
                    
                    s3.delete_object(Bucket=bucket, Key=filename)
                    print(f"Deleted audio file from R2: {filename}")
                except Exception as e:
                    print(f"Failed to delete audio file from R2: {e}")
            
            audio.is_active = False
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
else:
    print("[user_db] Using in-memory DB for user/task storage (local test mode)")
    import secrets
    from datetime import datetime
    _users = {}
    _tasks = {}

    def create_user(email: str, initial_credits: int = 0) -> str:
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

    def create_or_update_test_user(credit: int = 0):
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
            "started_at": None,
            "finished_at": None,
        }
        return _tasks[task_id]

    def update_task_status(task_id: str, status: str, result: dict = None, error: str = None):
        if task_id in _tasks:
            _tasks[task_id]["status"] = status
            if result is not None:
                _tasks[task_id]["result"] = result
            if error is not None:
                _tasks[task_id]["error"] = error
            
            # Set timestamps based on status
            if status == 'inprogress' and _tasks[task_id]["started_at"] is None:
                _tasks[task_id]["started_at"] = datetime.utcnow()
            elif status in ['finished', 'failed'] and _tasks[task_id]["finished_at"] is None:
                _tasks[task_id]["finished_at"] = datetime.utcnow()
            
            return _tasks[task_id]
        return None

    def get_task_by_id(task_id: str):
        return _tasks.get(task_id)

    # Credit management functions for new system
    def get_user_active_tasks_credits(api_key: str):
        """Get total credits needed for user's current active tasks (queued + inprogress)"""
        total_credits_needed = 0
        for task in _tasks.values():
            if task["user_api_key"] == api_key and task["status"] in ['queued', 'inprogress']:
                if task["request_payload"] and 'scenes' in task["request_payload"]:
                    # Calculate credits based on scene types
                    scenes = task["request_payload"]['scenes']
                    for scene in scenes:
                        if scene.get('type') == 'video':
                            if scene.get('prompt_video'):
                                total_credits_needed += 5  # AI video generation
                            elif scene.get('video_url'):
                                total_credits_needed += 1  # Existing video
                            else:
                                total_credits_needed += 1  # Default video scene
                        else:
                            total_credits_needed += 1  # Image scenes
        return total_credits_needed

    def can_user_create_task(api_key: str, new_task_scenes: list):
        """Check if user has enough credits for new task + existing active tasks"""
        user = _users.get(api_key)
        if not user:
            return False, "User not found"
        
        # Calculate credits needed for new task
        new_task_credits = 0
        for scene in new_task_scenes:
            if scene.get('type') == 'video':
                if scene.get('prompt_video'):
                    new_task_credits += 5  # AI video generation
                elif scene.get('video_url'):
                    new_task_credits += 1  # Existing video
                else:
                    new_task_credits += 1  # Default video scene
            else:
                new_task_credits += 1  # Image scenes
        
        # Get credits needed for existing active tasks
        active_tasks_credits = get_user_active_tasks_credits(api_key)
        total_credits_needed = active_tasks_credits + new_task_credits
        
        if user["credits"] >= total_credits_needed:
            return True, f"Sufficient credits. Available: {user['credits']}, Needed: {total_credits_needed} (Active tasks: {active_tasks_credits}, New task: {new_task_credits})"
        else:
            return False, f"Insufficient credits. Available: {user['credits']}, Needed: {total_credits_needed} (Active tasks: {active_tasks_credits}, New task: {new_task_credits})"

    def get_user_task_summary(api_key: str):
        """Get detailed summary of user's active tasks and credit usage"""
        user = _users.get(api_key)
        if not user:
            return None
        
        active_tasks = []
        total_credits_reserved = 0
        
        for task in _tasks.values():
            if task["user_api_key"] == api_key and task["status"] in ['queued', 'inprogress']:
                if task["request_payload"] and 'scenes' in task["request_payload"]:
                    scenes = task["request_payload"]['scenes']
                    task_credits = 0
                    scene_details = []
                    
                    for i, scene in enumerate(scenes):
                        scene_type = scene.get('type', 'unknown')
                        if scene_type == 'video':
                            if scene.get('prompt_video'):
                                scene_credits = 5
                                scene_desc = f"AI video generation: '{scene.get('prompt_video', '')[:50]}...'"
                            elif scene.get('video_url'):
                                scene_credits = 1
                                scene_desc = f"Existing video: {scene.get('video_url', '')[:50]}..."
                            else:
                                scene_credits = 1
                                scene_desc = "Video scene (default)"
                        else:
                            scene_credits = 1
                            scene_desc = f"Image scene: '{scene.get('prompt_image', scene.get('image_url', 'Generated/Uploaded'))[:50]}..."
                    
                        task_credits += scene_credits
                        scene_details.append({
                            "scene_index": i,
                            "type": scene_type,
                            "credits": scene_credits,
                            "description": scene_desc
                        })
                
                total_credits_reserved += task_credits
                active_tasks.append({
                    "task_id": task["id"],
                    "status": task["status"],
                    "created_at": task.get("created_at"),
                    "total_credits": task_credits,
                    "scenes": scene_details
                })
        
        return {
            "user_email": user["email"],
            "available_credits": user["credits"],
            "total_credits_reserved": total_credits_reserved,
            "credits_remaining_after_tasks": user["credits"] - total_credits_reserved,
            "active_tasks_count": len(active_tasks),
            "active_tasks": active_tasks
        } 