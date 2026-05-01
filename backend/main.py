import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, delete

from config import settings
from database import get_db, init_db, async_session
from models import User, SystemMetric, Alert
from auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user
)
from system_monitor import system_monitor
from websocket_manager import manager

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    
    class Config:
        orm_mode = True

class MetricResponse(BaseModel):
    id: int
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: Optional[float]
    network_sent: Optional[float]
    network_recv: Optional[float]
    
    class Config:
        orm_mode = True

class AlertResponse(BaseModel):
    id: int
    timestamp: datetime
    alert_type: str
    message: str
    value: float
    threshold: float
    is_read: bool
    
    class Config:
        orm_mode = True

class ThresholdUpdate(BaseModel):
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None

last_alert_time = {
    "cpu": None,
    "memory": None
}
last_alert_state = {
    "cpu": False,
    "memory": False
}
ALERT_COOLDOWN_SECONDS = 10

@app.on_event("startup")
async def startup_event():
    await init_db()
    asyncio.create_task(monitor_loop())

def should_send_alert(alert_type: str) -> bool:
    global last_alert_time
    now = datetime.utcnow()
    last_time = last_alert_time.get(alert_type)
    
    if last_time is None:
        last_alert_time[alert_type] = now
        return True
    
    time_diff = (now - last_time).total_seconds()
    if time_diff >= ALERT_COOLDOWN_SECONDS:
        last_alert_time[alert_type] = now
        return True
    
    return False

def check_recovery(metrics: Dict) -> list:
    global last_alert_state
    recoveries = []
    
    current_cpu_alert = metrics["cpu_usage"] >= settings.CPU_THRESHOLD
    current_memory_alert = metrics["memory_usage"] >= settings.MEMORY_THRESHOLD
    
    if last_alert_state["cpu"] and not current_cpu_alert:
        recoveries.append({
            "type": "cpu_recovery",
            "message": f"CPU 使用率已恢复正常: {metrics['cpu_usage']:.2f}%",
            "value": metrics["cpu_usage"],
            "threshold": settings.CPU_THRESHOLD
        })
    
    if last_alert_state["memory"] and not current_memory_alert:
        recoveries.append({
            "type": "memory_recovery",
            "message": f"内存使用率已恢复正常: {metrics['memory_usage']:.2f}%",
            "value": metrics["memory_usage"],
            "threshold": settings.MEMORY_THRESHOLD
        })
    
    last_alert_state["cpu"] = current_cpu_alert
    last_alert_state["memory"] = current_memory_alert
    
    return recoveries

async def monitor_loop():
    while True:
        try:
            metrics = system_monitor.get_all_metrics()
            
            if len(manager.active_connections) > 0:
                async with async_session() as session:
                    new_metric = SystemMetric(
                        timestamp=datetime.fromisoformat(metrics["timestamp"]),
                        cpu_usage=metrics["cpu_usage"],
                        memory_usage=metrics["memory_usage"],
                        disk_usage=metrics["disk_usage"],
                        network_sent=metrics["network_sent"],
                        network_recv=metrics["network_recv"]
                    )
                    session.add(new_metric)
                    
                    alerts = system_monitor.check_thresholds(metrics)
                    for alert in alerts:
                        if should_send_alert(alert["type"]):
                            new_alert = Alert(
                                alert_type=alert["type"],
                                message=alert["message"],
                                value=alert["value"],
                                threshold=alert["threshold"]
                            )
                            session.add(new_alert)
                            await manager.send_alert(alert)
                    
                    recoveries = check_recovery(metrics)
                    for recovery in recoveries:
                        await manager.send_alert(recovery)
                    
                    await session.commit()
                
                await manager.send_metrics(metrics)
            
            await asyncio.sleep(settings.WS_UPDATE_INTERVAL)
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(settings.WS_UPDATE_INTERVAL)

@app.post("/api/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await db.execute(select(User).where(User.username == user_data.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/api/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/metrics/current")
async def get_current_metrics(current_user: User = Depends(get_current_user)):
    metrics = system_monitor.get_all_metrics()
    return metrics

@app.get("/api/metrics/history", response_model=list[MetricResponse])
async def get_metrics_history(
    limit: int = 100,
    offset: int = 0,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(SystemMetric).order_by(desc(SystemMetric.timestamp))
    
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            query = query.where(SystemMetric.timestamp >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的开始时间格式")
    
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            query = query.where(SystemMetric.timestamp <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的结束时间格式")
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    metrics = result.scalars().all()
    return metrics

@app.get("/api/alerts", response_model=list[AlertResponse])
async def get_alerts(
    unread_only: bool = False,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert).order_by(desc(Alert.timestamp))
    
    if unread_only:
        query = query.where(Alert.is_read == False)
    
    query = query.limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()
    return alerts

@app.put("/api/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    alert.is_read = True
    await db.commit()
    return {"message": "告警已标记为已读"}

@app.get("/api/thresholds")
async def get_thresholds(current_user: User = Depends(get_current_user)):
    return {
        "cpu_threshold": settings.CPU_THRESHOLD,
        "memory_threshold": settings.MEMORY_THRESHOLD
    }

@app.put("/api/thresholds")
async def update_thresholds(
    thresholds: ThresholdUpdate,
    current_user: User = Depends(get_current_user)
):
    if thresholds.cpu_threshold is not None:
        if thresholds.cpu_threshold < 0 or thresholds.cpu_threshold > 100:
            raise HTTPException(status_code=400, detail="CPU 阈值必须在 0-100 之间")
        settings.CPU_THRESHOLD = thresholds.cpu_threshold
    
    if thresholds.memory_threshold is not None:
        if thresholds.memory_threshold < 0 or thresholds.memory_threshold > 100:
            raise HTTPException(status_code=400, detail="内存阈值必须在 0-100 之间")
        settings.MEMORY_THRESHOLD = thresholds.memory_threshold
    
    return {
        "cpu_threshold": settings.CPU_THRESHOLD,
        "memory_threshold": settings.MEMORY_THRESHOLD,
        "message": "阈值更新成功"
    }

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    client_id = f"client_{datetime.utcnow().timestamp()}"
    await manager.connect(websocket, client_id)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await manager.send_personal_message({"type": "pong"}, client_id)
                except json.JSONDecodeError:
                    pass
            except Exception:
                await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)

@app.get("/")
async def root():
    return {"message": "服务器性能监控系统 API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
