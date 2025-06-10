#!/usr/bin/env python3
"""
Standalone Camera Tool Module
=====================================

An independent camera capture system that runs autonomously.
Uses AIDB's exact camera implementation with face detection, reading material detection, 
and session management capabilities.

Extracted from AIDB Robot AI Assistant project while maintaining complete fidelity
to the original camera tool implementation and patterns.
"""

import os
import sys
import signal
import time
import threading
from pathlib import Path

# Import AIDB-style components (CRITICAL: Use exact imports)
from tools.camera_tool import CameraTool
from utils.settings import Settings
from utils.logging_config import setup_logging

# Set up logging using AIDB's pattern
logger = setup_logging("camera_tool")

class StandaloneCameraModule:
    """
    Standalone camera capture system following AIDB's camera tool pattern.
    
    Extracted and adapted from AIDB's camera processing while maintaining
    the core functionality and original practices.
    """
    
    def __init__(self, settings):
        """Initialize camera system - following AIDB's pattern"""
        self.settings = settings
        logger.info("Initializing camera system...")
        
        # Initialize camera tool using AIDB's exact pattern
        self.camera_tool = CameraTool(settings=self.settings, tool_name="camera_tool")
        
        # Set callbacks for continuous camera capture (following AIDB's main.py pattern)
        self.camera_tool.set_callbacks(
            on_image_captured=self._on_image_captured,
            on_frame_captured=self._on_preview_frame_captured
        )
        
        # Initialize state
        self.running = False
        self.session_active = False
        
        logger.info("Camera system initialized successfully")
        
    def _on_image_captured(self, image_path):
        """Handle session image capture - following AIDB's callback pattern"""
        logger.info(f"📸 Session image captured: {image_path}")
        print(f"📸 Session image saved: {os.path.basename(image_path)}")
        
    def _on_preview_frame_captured(self, frame_path):
        """Handle preview frame capture - following AIDB's callback pattern"""
        logger.debug(f"🎥 Preview frame updated: {frame_path}")
        # Preview frames are captured continuously in background mode
        # We only print occasionally to avoid spam
        if not hasattr(self, '_preview_count'):
            self._preview_count = 0
        self._preview_count += 1
        if self._preview_count % 30 == 0:  # Print every 30 frames (roughly every 30 seconds at 1fps)
            print(f"🎥 Camera running - {self._preview_count} frames captured (latest: {os.path.basename(frame_path)})")
        
    def start_background_mode(self):
        """Start camera in background mode - following AIDB's pattern"""
        if self.running:
            logger.warning("Camera system already running")
            return
            
        logger.info("Starting camera system in background mode...")
        print("Starting camera system in background mode...")
        print("Camera will capture frames continuously for face and reading material detection.")
        
        try:
            # Initialize the camera tool (AIDB's exact pattern)
            if not self.camera_tool.initialize_tool():
                logger.error("Failed to initialize camera tool")
                print("❌ Failed to initialize camera. Check camera permissions and availability.")
                return False
                
            # Start camera in background mode (no active session)
            result = self.camera_tool.process_command("start_camera", {})
            if not result.get("success", False):
                logger.error(f"Failed to start camera: {result.get('message', 'Unknown error')}")
                print(f"❌ Failed to start camera: {result.get('message', 'Unknown error')}")
                return False
                
            self.running = True
            logger.info("Camera system started successfully in background mode")
            print("✅ Camera system active! Running in background mode...")
            print("   - Face detection: " + ("Enabled" if self.settings.camera.face_detection_enabled else "Disabled"))
            print("   - Reading material detection: " + ("Enabled" if self.settings.camera.reading_material_detection_enabled else "Disabled"))
            print("   - Preview updates every ~1 second")
            print("   - Use Ctrl+C to stop or start a session for image saving")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error starting camera system: {e}")
            print(f"❌ Error starting camera: {e}")
            return False
            
    def start_session(self, session_id=None):
        """Start a camera session - following AIDB's pattern"""
        if not self.running:
            print("❌ Camera system not running. Start background mode first.")
            return False
            
        if self.session_active:
            print("⚠️ Session already active")
            return True
            
        logger.info("Starting camera session...")
        print("📸 Starting camera session...")
        
        try:
            result = self.camera_tool.process_command("start_session", {"session_id": session_id})
            if result.get("success", False):
                self.session_active = True
                session_info = result.get("session_info", {})
                session_id = session_info.get("session_id", "unknown")
                session_dir = session_info.get("session_dir", "")
                
                logger.info(f"Camera session started: {session_id}")
                print(f"✅ Session started: {session_id}")
                print(f"   Images will be saved to: {session_dir}")
                print("   Images are captured automatically based on detection and interval settings")
                return True
            else:
                logger.error(f"Failed to start session: {result.get('message', 'Unknown error')}")
                print(f"❌ Failed to start session: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.exception(f"Error starting session: {e}")
            print(f"❌ Error starting session: {e}")
            return False
            
    def end_session(self):
        """End the current camera session - following AIDB's pattern"""
        if not self.session_active:
            print("⚠️ No active session to end")
            return None
            
        logger.info("Ending camera session...")
        print("📸 Ending camera session...")
        
        try:
            result = self.camera_tool.process_command("end_session", {})
            if result.get("success", False):
                self.session_active = False
                session_data = result.get("session_data", {})
                images = session_data.get("images", [])
                session_id = session_data.get("session_id", "unknown")
                
                logger.info(f"Session ended: {session_id} with {len(images)} images")
                print(f"✅ Session ended: {session_id}")
                print(f"   Total images captured: {len(images)}")
                if images:
                    print(f"   Session directory: {os.path.dirname(images[0]['filename'])}")
                return session_data
            else:
                logger.error(f"Failed to end session: {result.get('message', 'Unknown error')}")
                print(f"❌ Failed to end session: {result.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.exception(f"Error ending session: {e}")
            print(f"❌ Error ending session: {e}")
            return None
            
    def get_current_frame(self):
        """Get the current camera frame - following AIDB's pattern"""
        if not self.running:
            print("❌ Camera system not running")
            return None
            
        try:
            result = self.camera_tool.process_command("get_current_frame", {})
            if result.get("success", False):
                frame_info = {
                    "frame_path": result.get("frame_path"),
                    "timestamp": result.get("timestamp")
                }
                print(f"📷 Current frame: {os.path.basename(frame_info['frame_path'])}")
                return frame_info
            else:
                print(f"⚠️ No current frame available: {result.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.exception(f"Error getting current frame: {e}")
            print(f"❌ Error getting current frame: {e}")
            return None
            
    def get_captured_images(self):
        """Get list of captured session images - following AIDB's pattern"""
        try:
            result = self.camera_tool.process_command("get_captured_images", {})
            if result.get("success", False):
                session_data = result.get("session_data", {})
                images = session_data.get("images", [])
                session_id = session_data.get("session_id", "unknown")
                
                print(f"📋 Session {session_id}: {len(images)} images")
                for i, img in enumerate(images, 1):
                    print(f"   {i}. {os.path.basename(img['filename'])} - {img.get('datetime', 'unknown time')}")
                return session_data
            else:
                print("⚠️ No session data available")
                return None
                
        except Exception as e:
            logger.exception(f"Error getting captured images: {e}")
            print(f"❌ Error getting captured images: {e}")
            return None
            
    def stop(self):
        """Stop the camera system - following AIDB's cleanup pattern"""
        if not self.running:
            return
            
        logger.info("Stopping camera system...")
        print("Stopping camera system...")
        
        try:
            # End any active session first
            if self.session_active:
                self.end_session()
                
            # Stop the camera (AIDB's exact cleanup sequence)
            result = self.camera_tool.process_command("stop_camera", {})
            if result.get("success", False):
                logger.info("Camera stopped successfully")
                print("✅ Camera stopped")
            else:
                logger.warning(f"Camera stop returned: {result.get('message', 'Unknown status')}")
                
            # Shutdown the tool
            self.camera_tool.shutdown_tool()
            self.running = False
            
            logger.info("Camera system stopped successfully")
            print("✅ Camera system stopped")
        except Exception as e:
            logger.exception(f"Error stopping camera system: {e}")
            print(f"⚠️ Error during shutdown: {e}")

def setup_signal_handlers(camera_module):
    """Set up signal handlers - following AIDB's pattern"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        logger.info(f"Received signal {signum}. Shutting down...")
        camera_module.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def interactive_mode(camera_module):
    """Interactive command mode for controlling the camera"""
    print("\n" + "=" * 60)
    print("Interactive Camera Control")
    print("=" * 60)
    print("Commands:")
    print("  start     - Start camera session (save images)")
    print("  end       - End current session")
    print("  frame     - Get current frame info")
    print("  images    - List captured images in current/last session")
    print("  status    - Show camera status")
    print("  help      - Show this help")
    print("  quit      - Exit the program")
    print("=" * 60)
    
    while camera_module.running:
        try:
            command = input("\ncamera> ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                break
            elif command == 'start':
                camera_module.start_session()
            elif command == 'end':
                camera_module.end_session()
            elif command == 'frame':
                camera_module.get_current_frame()
            elif command == 'images':
                camera_module.get_captured_images()
            elif command == 'status':
                print(f"Camera running: {'Yes' if camera_module.running else 'No'}")
                print(f"Session active: {'Yes' if camera_module.session_active else 'No'}")
                if hasattr(camera_module, '_preview_count'):
                    print(f"Frames captured: {camera_module._preview_count}")
            elif command == 'help':
                print("Commands: start, end, frame, images, status, help, quit")
            elif command == '':
                continue  # Empty input, just continue
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print(f"Error processing command: {e}")

def main():
    """Main function - following AIDB's initialization pattern"""
    print("📸 Standalone Camera Tool Module")
    print("Extracted from AIDB Robot AI Assistant project")
    print("=" * 50)
    
    try:
        # Load settings using AIDB's system
        logger.info("Loading settings...")
        settings = Settings()
        logger.info("Settings loaded successfully")
        
        # Display current configuration
        print(f"Camera device: {settings.camera.device}")
        print(f"Capture interval: {settings.camera.capture_interval}s")
        print(f"Image quality: {settings.camera.image_quality}%")
        print(f"Face detection: {'Enabled' if settings.camera.face_detection_enabled else 'Disabled'}")
        print(f"Reading material detection: {'Enabled' if settings.camera.reading_material_detection_enabled else 'Disabled'}")
        print(f"Image directory: {settings.camera.image_dir}")
        print()
        
        # Initialize camera module
        camera_module = StandaloneCameraModule(settings)
        
        # Set up signal handlers
        setup_signal_handlers(camera_module)
        
        # Start camera in background mode
        if not camera_module.start_background_mode():
            print("❌ Failed to start camera system. Exiting.")
            sys.exit(1)
            
        # Run interactive mode
        try:
            interactive_mode(camera_module)
        except KeyboardInterrupt:
            pass
            
        # Clean shutdown
        camera_module.stop()
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start camera system: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 