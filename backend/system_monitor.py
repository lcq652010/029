import psutil
import os
import platform
from datetime import datetime
from typing import Dict, Any
from config import settings

class SystemMonitor:
    def __init__(self):
        self.last_net_io = None
        self._init_cpu_usage()
    
    def _init_cpu_usage(self):
        psutil.cpu_percent(interval=0)
    
    def get_cpu_usage(self) -> float:
        return psutil.cpu_percent(interval=0)
    
    def get_memory_usage(self) -> float:
        mem = psutil.virtual_memory()
        return mem.percent
    
    def get_memory_info(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent
        }
    
    def get_disk_usage(self) -> float:
        system = platform.system()
        if system == 'Windows':
            partitions = psutil.disk_partitions()
            if partitions:
                disk = psutil.disk_usage(partitions[0].mountpoint)
                return disk.percent
            return 0.0
        else:
            disk = psutil.disk_usage('/')
            return disk.percent
    
    def get_network_io(self) -> Dict[str, Any]:
        net_io = psutil.net_io_counters()
        current_time = datetime.now()
        
        if self.last_net_io is None:
            self.last_net_io = (net_io, current_time)
            return {
                "bytes_sent_per_sec": 0,
                "bytes_recv_per_sec": 0
            }
        
        last_io, last_time = self.last_net_io
        time_diff = (current_time - last_time).total_seconds()
        
        if time_diff <= 0:
            return {
                "bytes_sent_per_sec": 0,
                "bytes_recv_per_sec": 0
            }
        
        bytes_sent_per_sec = (net_io.bytes_sent - last_io.bytes_sent) / time_diff
        bytes_recv_per_sec = (net_io.bytes_recv - last_io.bytes_recv) / time_diff
        
        self.last_net_io = (net_io, current_time)
        
        return {
            "bytes_sent_per_sec": bytes_sent_per_sec,
            "bytes_recv_per_sec": bytes_recv_per_sec
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        cpu = self.get_cpu_usage()
        memory = self.get_memory_usage()
        disk = self.get_disk_usage()
        network = self.get_network_io()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_usage": cpu,
            "memory_usage": memory,
            "disk_usage": disk,
            "network_sent": network["bytes_sent_per_sec"],
            "network_recv": network["bytes_recv_per_sec"],
            "cpu_alert": cpu >= settings.CPU_THRESHOLD,
            "memory_alert": memory >= settings.MEMORY_THRESHOLD
        }
    
    def check_thresholds(self, metrics: Dict[str, Any]) -> list:
        alerts = []
        
        if metrics["cpu_usage"] >= settings.CPU_THRESHOLD:
            alerts.append({
                "type": "cpu",
                "message": f"CPU 使用率超过阈值: {metrics['cpu_usage']:.2f}%",
                "value": metrics["cpu_usage"],
                "threshold": settings.CPU_THRESHOLD
            })
        
        if metrics["memory_usage"] >= settings.MEMORY_THRESHOLD:
            alerts.append({
                "type": "memory",
                "message": f"内存使用率超过阈值: {metrics['memory_usage']:.2f}%",
                "value": metrics["memory_usage"],
                "threshold": settings.MEMORY_THRESHOLD
            })
        
        return alerts

system_monitor = SystemMonitor()
