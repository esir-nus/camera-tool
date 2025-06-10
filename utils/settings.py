"""
Settings module for Robot AI using Pydantic models.

This module provides a structured configuration system using Pydantic BaseSettings,
which loads configuration from environment variables with support for .env files.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path


class MemorySettings(BaseModel):
    """Settings for memory management"""
    max_memory_turns: int = Field(5, description="Maximum number of conversation turns to keep in memory")


class CameraSettings(BaseModel):
    """Settings for camera tool"""
    device: Union[int, str] = Field(0, description="Camera device index or device path")
    capture_interval: float = Field(1.0, description="Seconds between captures")
    image_quality: int = Field(95, description="JPEG quality (1-100)")
    image_dir: str = Field("logs/camera_captures", description="Directory for storing captures")
    image_width: int = Field(640, description="Image width in pixels") 
    image_height: int = Field(480, description="Image height in pixels")
    # Detection model parameters
    models_dir: str = Field("models/cv", description="Directory containing detection models")
    face_cascade_file: str = Field("haarcascade_frontalface_default.xml", description="Filename for face detection cascade")
    reading_material_model: str = Field("read_material-yolo11n-best.pt", description="Filename for reading material detection model")
    face_detection_enabled: bool = Field(True, description="Whether face detection is enabled")
    reading_material_detection_enabled: bool = Field(True, description="Whether reading material detection is enabled")
    detection_confidence: float = Field(0.5, description="Confidence threshold for detections (0.0-1.0)")
    use_ncnn: bool = Field(False, description="Whether to use NCNN optimization for YOLO models")
    center_threshold_percent: int = Field(15, description="Percentage of image width to determine if an object is centered (1-50)")


class QueryTool(BaseModel):
    """Settings for AI models"""
    llm_backend: str = Field("gemini", description="AI model to use")
    qwen_api_key: str = Field("", description="API key for Qwen API")


class AISettings(BaseModel):
    """Settings for AI models"""
    model: str = Field("gemini-2.0-flash", description="AI model to use")
    api_key: str = Field("", description="API key for the AI service")
    base_url: Optional[str] = Field(None, description="Base URL for the AI API")
    use_vision: bool = Field(True, description="Whether to use vision capabilities")


class TuyaSettings(BaseModel):
    """Settings for Tuya smart devices"""
    access_id: str = Field("", description="Tuya API access ID")
    access_key: str = Field("", description="Tuya API access key")
    api_endpoint: str = Field("https://openapi.tuyacn.com/", description="Tuya API endpoint URL")
    device_id: str = Field("", description="Tuya device ID")


class TTSSettings(BaseModel):
    """Settings for text-to-speech"""
    backend: str = Field("piper", description="TTS backend to use (e.g., piper, gtts)")
    piper_model_path: str = Field("models/voices/en_GB-alan-low.onnx", description="Path to Piper model file")
    piper_binary_path: str = Field("models/voices/piper", description="Path to Piper binary executable")
    processing_interval: float = Field(2.0, description="TTS processing interval in seconds")
    qwen_api_key: str = Field("", description="API key for Qwen TTS service")


class RobotSettings(BaseModel):
    """Settings for robot control"""
    nav_url: str = Field("http://10.0.3.101:5000/", description="URL for robot navigation API")
    arm_url: str = Field("http://10.0.3.101:5001/", description="URL for robotic arm API")


class ToolEnableSettings(BaseModel):
    """Settings for enabling/disabling specific tools"""
    browser_tool: bool = Field(True, description="Enable browser automation tool")
    query_tool: bool = Field(True, description="Enable natural language query tool")
    light_control: bool = Field(True, description="Enable Tuya light control tool")
    robot_navigation: bool = Field(True, description="Enable robot navigation tool")
    robotic_arm: bool = Field(True, description="Enable robotic arm tool")


class AudioSettings(BaseModel):
    """Settings for audio tool (wake word, streaming, etc)"""
    sample_rate: int = Field(16000, description="Audio sample rate (Hz)")
    chunk_duration: float = Field(0.08, description="Audio chunk duration in seconds")
    pre_buffer_sec: float = Field(1.0, description="Seconds of audio to keep in rolling buffer before wake word")
    wake_threshold: float = Field(0.5, description="Wake word detection threshold (0-1)")
    silence_threshold: float = Field(0.005, description="Audio level threshold to detect silence")
    silence_duration: float = Field(2.0, description="Duration of silence to trigger end of recording (seconds)")
    wakeword_model: str = Field("models/wakeup-word/hey_neo.onnx", description="Path to the wake word model file")
    enable_noise_suppression: bool = Field(True, description="Enable Speex noise suppression for wake word detection")
    asr_backend: str = Field("whisper", description="ASR backend to use (e.g., whisper, vosk)")
    whisper_model: str = Field("base", description="Whisper model to use for ASR")
    cloud_asr_api_key: str = Field("", description="API key for cloud ASR service")


class Settings(BaseSettings):
    """Main settings class that contains all submodule settings"""
    
    memory: MemorySettings = Field(default_factory=MemorySettings)
    camera: CameraSettings = Field(default_factory=CameraSettings) 
    ai: AISettings = Field(default_factory=AISettings)
    gemini: AISettings = Field(default_factory=lambda: AISettings(model="gemini-2.0-flash"))
    query: QueryTool = Field(default_factory=QueryTool)
    tuya: TuyaSettings = Field(default_factory=TuyaSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    robot: RobotSettings = Field(default_factory=RobotSettings)
    tools: ToolEnableSettings = Field(default_factory=ToolEnableSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )