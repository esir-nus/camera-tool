import cv2
import os
import time
import threading
import logging
import math
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from utils.logging_config import setup_logging
from tools.tool_interface import ToolInterface
from utils.settings import Settings

# Set up a logger specific to this module
logger = setup_logging("camera_tool")

class CameraTool(ToolInterface):
    """Camera tool that captures images continuously with support for background mode and active sessions."""
    
    def __init__(self, settings: Settings, tool_name: str):
        """Initialize the Camera tool with settings parameters."""
        super().__init__(settings, tool_name)
        
        # Configuration parameters
        self.camera_device = settings.camera.device
        self.capture_interval = settings.camera.capture_interval  # seconds
        self.image_quality = settings.camera.image_quality  # JPEG quality
        self.image_dir = settings.camera.image_dir
        self.image_width = settings.camera.image_width
        self.image_height = settings.camera.image_height
        
        # Detection models parameters - now from settings
        self.models_dir = settings.camera.models_dir
        self.face_cascade_file = settings.camera.face_cascade_file
        self.reading_material_model = settings.camera.reading_material_model
        self.face_detection_enabled = settings.camera.face_detection_enabled
        self.reading_material_detection_enabled = settings.camera.reading_material_detection_enabled
        self.detection_confidence = settings.camera.detection_confidence
        self.use_ncnn = settings.camera.use_ncnn
        
        # Detection model objects
        self.face_cascade = None
        self.reading_material_detector = None
        self.model_type = None  # Can be 'ultralytics', 'ncnn', None
        
        # State variables for the camera
        self.camera_running = False       # Whether the camera capture thread is running
        self.frame_grabber_thread = None  # Thread dedicated to grabbing frames as fast as possible
        self.camera = None                # OpenCV camera object
        self.next_process_time = 0        # When to process the next frame
        
        # State variables for session mode
        self.session_active = False       # Whether a named session is active (saving to disk)
        self.session_id = None            # ID of current capture session
        self.session_dir = None           # Directory for current capture session
        self.captured_images = []         # List of images captured in current session
        
        # In-memory frame buffers
        self.current_raw_frame = None     # Latest raw frame from camera (unprocessed)
        self.current_frame = None         # Latest processed frame (with annotations)
        self.current_frame_lock = threading.RLock()  # Lock for thread-safe access to frames
        self.last_frame_time = 0          # Timestamp of the last captured frame
        self.last_processed_time = 0      # Timestamp of the last processed frame
        
        # Callbacks
        self.on_image_captured = None     # Callback for when new images are captured
        self.on_frame_captured = None     # Callback for when any frame is captured (even in background mode)
        
        # Ensure image directory exists
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Background preview directory for temporary frames
        self.preview_dir = os.path.join(self.image_dir, "preview")
        os.makedirs(self.preview_dir, exist_ok=True)
        self.preview_file = os.path.join(self.preview_dir, "current_frame.jpg")
    
    def initialize_tool(self) -> bool:
        """Initialize camera tool, detection models, and start continuous background capture."""
        try:
            # Test camera availability
            test_camera = cv2.VideoCapture(self.camera_device)
            if test_camera.isOpened():
                success, _ = test_camera.read()
                test_camera.release()
                if not success:
                    logger.error(f"Camera opened but could not read frame from device {self.camera_device}")
                    return False
            else:
                logger.error(f"Could not open camera device {self.camera_device}")
                return False
            
            # Load face detection model if enabled
            if self.face_detection_enabled:
                face_cascade_path = os.path.join(self.models_dir, self.face_cascade_file)
                if os.path.exists(face_cascade_path):
                    self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
                    logger.info(f"Face detection model loaded from {face_cascade_path}")
                else:
                    logger.warning(f"Face detection model not found at {face_cascade_path}. Face detection disabled.")
                    self.face_detection_enabled = False
            
            # Load reading material detection model if enabled
            if self.reading_material_detection_enabled:
                try:
                    # Try to import YOLO from ultralytics
                    from ultralytics import YOLO
                    
                    # Set model path
                    model_path = os.path.join(self.models_dir, self.reading_material_model)
                    model_base_name = os.path.splitext(os.path.basename(model_path))[0]
                    ncnn_output_dir = os.path.join(self.models_dir, f"{model_base_name}_ncnn_model")
                    
                    if self.use_ncnn:
                        # Check if NCNN model exists, if not, convert from PyTorch
                        if not os.path.exists(ncnn_output_dir):
                            logger.info(f"NCNN model not found, converting from {model_path}...")
                            try:
                                # Load the PyTorch model and export to NCNN
                                pt_model = YOLO(model_path)
                                pt_model.export(format="ncnn")
                                logger.info(f"NCNN model created at {ncnn_output_dir}")
                            except Exception as e:
                                logger.error(f"Failed to convert to NCNN model: {e}")
                                self.use_ncnn = False
                        else:
                            logger.info(f"NCNN model found at {ncnn_output_dir}")
                        
                        # Load NCNN model if conversion succeeded or already exists
                        if self.use_ncnn:
                            self.reading_material_detector = YOLO(ncnn_output_dir)
                            self.model_type = 'ncnn'
                            logger.info(f"Reading material NCNN model loaded from {ncnn_output_dir}")
                    
                    # If not using NCNN or NCNN loading failed, use standard PyTorch model
                    if not self.use_ncnn:
                        if os.path.exists(model_path):
                            self.reading_material_detector = YOLO(model_path)
                            self.model_type = 'ultralytics'
                            logger.info(f"Reading material PyTorch model loaded from {model_path}")
                        else:
                            logger.warning(f"Reading material model not found at {model_path}. Reading material detection disabled.")
                            self.reading_material_detection_enabled = False
                    
                except ImportError:
                    logger.warning("Ultralytics YOLO not available. Reading material detection disabled.")
                    self.reading_material_detection_enabled = False
                except Exception as e:
                    logger.error(f"Failed to load reading material model: {e}")
                    self.reading_material_detection_enabled = False
                    
            # Start background camera capture immediately
            logger.info("Starting continuous background camera capture")
            self._start_camera()
                    
            logger.info(f"Camera initialization successful on device {self.camera_device}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Camera Tool: {e}")
            return False
    
    def set_callbacks(self, on_image_captured=None, on_frame_captured=None):
        """Set callbacks for image and frame captures."""
        self.on_image_captured = on_image_captured  # Called when a frame is saved to disk in session mode
        self.on_frame_captured = on_frame_captured  # Called when any frame is captured, even in background mode
    
    def process_command(self, command_name: str, parameters: Dict[str, Any]) -> Any:
        """Process camera commands."""
        logger.warning(f"CAMERA TOOL - Received command '{command_name}' with parameters: {parameters}")
        
        if command_name == "start_session":
            # Start a named session (save to disk)
            session_id = parameters.get('session_id', None)
            return self._start_session(session_id)
            
        elif command_name == "end_session":
            # End the current session but keep camera running in background mode
            logger.warning("CAMERA TOOL - Processing end_session command")
            result = self._end_session()
            logger.warning("CAMERA TOOL - Completed end_session, returning result")
            return result
            
        elif command_name == "get_captured_images":
            # Get images captured in the current or last session
            logger.warning("CAMERA TOOL - Processing get_captured_images command")
            return self._get_captured_images()
            
        elif command_name == "get_current_frame":
            # Get the latest frame buffer regardless of session status
            logger.warning("CAMERA TOOL - Processing get_current_frame command")
            return self._get_current_frame()
            
        elif command_name == "stop_camera":
            # Stop the camera completely (use for shutdown)
            logger.warning("CAMERA TOOL - Processing stop_camera command")
            return self._stop_camera()
            
        elif command_name == "start_camera":
            # Start camera in background mode (if not already running)
            logger.warning("CAMERA TOOL - Processing start_camera command")
            return self._start_camera()
            
        elif command_name == "get_detection_status":
            # Get status of detection models
            logger.warning("CAMERA TOOL - Processing get_detection_status command")
            return self._get_detection_status()
            
        else:
            logger.warning(f"CAMERA TOOL - Unknown command '{command_name}' for {self.tool_name}")
            return False
    
    def _get_detection_status(self):
        """Get the current status of detection models."""
        return {
            "face_detection": {
                "enabled": self.face_detection_enabled,
                "model_loaded": self.face_cascade is not None
            },
            "reading_material_detection": {
                "enabled": self.reading_material_detection_enabled,
                "model_loaded": self.reading_material_detector is not None,
                "model_type": self.model_type,
                "use_ncnn": self.use_ncnn and self.model_type == 'ncnn'
            },
            "camera_status": {
                "running": self.camera_running,
                "session_active": self.session_active,
                "session_id": self.session_id
            }
        }
    
    def shutdown_tool(self):
        """Clean up resources when shutting down."""
        logger.info("Shutting down Camera Tool")
        self._stop_camera()
    
    def _create_session_directory(self, session_id):
        """Create a directory for this session's images."""
        session_dir = os.path.join(self.image_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        logger.info(f"Created session directory: {session_dir}")
        return session_dir
    
    def _start_camera(self):
        """Start camera in background mode."""
        if self.camera_running:
            logger.info("Camera is already running.")
            return {
                "success": True,
                "message": "Camera is already running"
            }
        
        logger.info("Starting camera in background mode")
        
        try:
            # Reset state
            self.camera_running = True
            self.next_process_time = 0  # Process a frame immediately
            
            # Start frame grabber thread to continuously read frames without delay
            self.frame_grabber_thread = threading.Thread(target=self._frame_grabber_loop, daemon=True)
            self.frame_grabber_thread.start()
            
            return {
                "success": True,
                "message": "Camera started successfully in background mode"
            }
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.camera_running = False
            return {
                "success": False,
                "message": f"Failed to start camera: {e}"
            }
    
    def _start_session(self, session_id=None):
        """Start a named session to save captured frames to disk."""
        if self.session_active:
            logger.warning("A session is already active. End it first.")
            return {
                "success": False,
                "message": "A session is already active. End it first."
            }
        
        try:
            # Generate a session ID if none provided
            self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Starting camera session with ID: {self.session_id}")
            
            # Create a dedicated directory for this session
            self.session_dir = self._create_session_directory(self.session_id)
            
            # Reset captured images list
            self.captured_images = []
            
            # Set session state to active
            self.session_active = True
            
            # Make sure the camera is running
            if not self.camera_running:
                camera_result = self._start_camera()
                if not camera_result.get("success", False):
                    self.session_active = False
                    return {
                        "success": False,
                        "message": f"Failed to start camera: {camera_result.get('message', 'Unknown error')}"
                    }
            
            return {
                "success": True,
                "message": f"Session started successfully: {self.session_id}",
                "session_info": {
                    "session_id": self.session_id,
                    "session_dir": self.session_dir
                }
            }
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            self.session_active = False
            return {
                "success": False,
                "message": f"Failed to start session: {e}"
            }
    
    def _detect_faces(self, frame):
        """Detect faces in the frame and return bounding boxes."""
        if not self.face_detection_enabled or self.face_cascade is None or frame is None:
            return []
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            return faces
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def _detect_reading_material(self, frame):
        """Detect reading material in the frame using YOLO model."""
        if not self.reading_material_detection_enabled or self.reading_material_detector is None or frame is None:
            return []
        
        try:
            # Run YOLO detection
            results = self.reading_material_detector(frame, conf=self.detection_confidence)
            
            # Extract bounding boxes from results
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get box coordinates (convert to integers for drawing)
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf.item()
                    detections.append({
                        'box': [int(x1), int(y1), int(x2-x1), int(y2-y1)],  # x, y, w, h format
                        'confidence': conf
                    })
            
            return detections
        except Exception as e:
            logger.error(f"Error in reading material detection: {e}")
            return []
    
    def _annotate_frame(self, frame):
        """
        Add face and reading material annotations to the frame.
        This is used for preview display only.
        """
        if frame is None:
            return None
            
        try:
            annotated_frame = frame.copy()
            
            # Get image dimensions for center calculations
            img_height, img_width = frame.shape[:2]
            img_center_x = img_width // 2
            img_center_y = img_height // 2
            
            # Use center threshold from settings
            center_threshold_percent = self.settings.camera.center_threshold_percent
            center_threshold_px = (img_width * center_threshold_percent) // 100
            
            # Detect and annotate faces
            faces = self._detect_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(annotated_frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Detect and annotate reading materials
            reading_materials = self._detect_reading_material(frame)
            for detection in reading_materials:
                x, y, w, h = detection['box']
                conf = detection['confidence']
                
                # Calculate center of the bounding box
                bbox_center_x = x + (w // 2)
                bbox_center_y = y + (h // 2)
                
                # Calculate distance from image center
                distance_from_center = math.sqrt((bbox_center_x - img_center_x)**2 + 
                                               (bbox_center_y - img_center_y)**2)
                
                # Determine if the object is centered
                is_centered = distance_from_center <= center_threshold_px
                
                # Choose color based on distance from center (green if centered, red if not)
                color = (0, 255, 0) if is_centered else (0, 0, 255)
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
                
                # Add label with confidence
                label = f'Reading Material: {conf:.2f}'
                cv2.putText(annotated_frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # If not centered, draw an arrow pointing from the bbox center to the image center
                if not is_centered:
                    # Calculate arrow vector (from bbox center to image center)
                    arrow_dx = img_center_x - bbox_center_x
                    arrow_dy = img_center_y - bbox_center_y
                    
                    # Normalize and scale the vector to create the arrow
                    arrow_length = math.sqrt(arrow_dx**2 + arrow_dy**2)
                    arrow_scale = min(50, arrow_length / 2)  # Limit arrow length
                    
                    if arrow_length > 0:  # Avoid division by zero
                        arrow_dx = int((arrow_dx / arrow_length) * arrow_scale)
                        arrow_dy = int((arrow_dy / arrow_length) * arrow_scale)
                        
                        # Calculate arrow start and end points
                        arrow_start = (bbox_center_x, bbox_center_y)
                        arrow_end = (bbox_center_x + arrow_dx, bbox_center_y + arrow_dy)
                        
                        # Draw the arrow
                        cv2.arrowedLine(annotated_frame, arrow_start, arrow_end, (0, 255, 255), 2, tipLength=0.3)
            
            # Add session status indicator text
            if self.session_active:
                cv2.putText(annotated_frame, f"Recording: {self.session_id}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            return annotated_frame
        except Exception as e:
            logger.error(f"Error annotating frame: {e}")
            return frame  # Return original frame if annotation fails
    
    def _frame_grabber_loop(self):
        """
        Dedicated thread that continuously grabs frames as quickly as possible
        to prevent buffer buildup, which causes lag on Raspberry Pi.
        """
        logger.info("Frame grabber thread started")
        
        try:
            # Open camera
            self.camera = cv2.VideoCapture(self.camera_device)
            if not self.camera.isOpened():
                logger.error(f"Could not open camera device {self.camera_device}")
                self.camera_running = False
                return
                
            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)
            
            # Buffer size optimization
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Continuous frame grabbing to prevent buffer buildup
            while self.camera_running:
                # Grab frame as quickly as possible
                ret, frame = self.camera.read()
                
                if ret:
                    # Store the frame with timestamp in shared buffer
                    with self.current_frame_lock:
                        self.current_raw_frame = frame
                        self.last_frame_time = time.time()
                        
                    # Check if it's time to process a frame (this is now done in the main thread)
                    self._process_frame_if_needed()
                else:
                    # Small delay to avoid CPU thrashing if camera fails
                    logger.warning("Failed to capture image from camera")
                    time.sleep(0.1)
                    
                # No delay here - grab frames as fast as hardware allows
                    
        except Exception as e:
            logger.error(f"Error in frame grabber thread: {e}")
        finally:
            # Clean up camera resource
            if self.camera and self.camera.isOpened():
                self.camera.release()
            self.camera = None
            logger.info("Frame grabber thread finished")
    
    def _process_frame_if_needed(self):
        """
        Process the latest frame if it's time to do so.
        This runs in the main camera tool thread.
        """
        current_time = time.time()
        
        # Check if it's time to process a frame
        if current_time < self.next_process_time:
            return
            
        # Set the next processing time
        self.next_process_time = current_time + self.capture_interval
        
        # Get a copy of the latest frame
        process_frame = None
        timestamp = 0
        
        with self.current_frame_lock:
            if self.current_raw_frame is not None:
                process_frame = self.current_raw_frame.copy()
                timestamp = self.last_frame_time
        
        if process_frame is None:
            return
        
        # Process the frame
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        ms = int((timestamp - int(timestamp)) * 1000)
        
        # Create annotated frame for preview only
        annotated_frame = self._annotate_frame(process_frame)
        
        # Store processed frame in memory buffer (with lock for thread safety)
        with self.current_frame_lock:
            self.current_frame = annotated_frame
            self.last_processed_time = timestamp
        
        # Save preview frame to disk for UI access (with annotations)
        try:
            cv2.imwrite(self.preview_file, annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])
        except Exception as e:
            logger.error(f"Error saving preview frame: {e}")
        
        # Call frame captured callback if registered
        if self.on_frame_captured:
            self.on_frame_captured(self.preview_file)
        
        # If we're in session mode, save to the session directory (original frame without annotations)
        if self.session_active and self.session_dir:
            # Create filename with readable date format
            image_filename = f"{date_str}_{ms:03d}.jpg"
            full_path = os.path.join(self.session_dir, image_filename)
            
            # Save the original image to the session directory (no annotations)
            try:
                cv2.imwrite(full_path, process_frame, [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])
                logger.debug(f"Image captured and saved to {full_path}")
                
                # Add to the list of captured images for this session
                self.captured_images.append({
                    "filename": full_path,
                    "timestamp": timestamp,
                    "datetime": f"{date_str}_{ms:03d}",
                    "session_id": self.session_id,
                    "detections": {
                        "faces": len(self._detect_faces(process_frame)),
                        "reading_materials": len(self._detect_reading_material(process_frame))
                    }
                })
                
                # Call the session image captured callback if registered
                if self.on_image_captured:
                    self.on_image_captured(full_path)
            except Exception as e:
                logger.error(f"Error saving session image: {e}")
    
    def _end_session(self):
        """End the current session but keep camera running in background mode."""
        if not self.session_active:
            logger.warning("No active session to end.")
            return {
                "success": False,
                "message": "No active session to end",
                "session_data": {"session_id": self.session_id, "images": self.captured_images}
            }
        
        logger.info("Ending camera session.")
        
        try:
            # Get captured images before changing state
            captured_result = self._get_captured_images()
            captured_data = captured_result.get('session_data', {})
            images = captured_data.get('images', [])
            
            # Update session state
            self.session_active = False
            
            logger.info(f"Session ended with {len(images)} captured images")
            return {
                "success": True,
                "message": f"Session ended successfully with {len(images)} images",
                "session_data": captured_data
            }
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return {
                "success": False,
                "message": f"Error ending session: {e}",
                "session_data": {"session_id": self.session_id, "images": self.captured_images}
            }
    
    def _stop_camera(self):
        """Stop the camera completely."""
        try:
            # First end any active session
            if self.session_active:
                self._end_session()
            
            if not self.camera_running:
                logger.warning("Camera is not currently running.")
                return {
                    "success": True,
                    "message": "Camera is already stopped"
                }
            
            logger.info("Stopping camera completely.")
            self.camera_running = False
            
            # Wait for frame grabber thread to finish
            if self.frame_grabber_thread and self.frame_grabber_thread.is_alive():
                logger.info("Waiting for frame grabber thread to finish...")
                self.frame_grabber_thread.join(timeout=5.0)
                if self.frame_grabber_thread.is_alive():
                    logger.warning("Frame grabber thread did not exit in time, proceeding anyway")
            
            # Clear frame buffers
            with self.current_frame_lock:
                self.current_raw_frame = None
                self.current_frame = None
            
            return {
                "success": True,
                "message": "Camera stopped successfully"
            }
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
            return {
                "success": False,
                "message": f"Error stopping camera: {e}"
            }
    
    def _get_current_frame(self):
        """Get the latest captured frame along with detection data."""
        with self.current_frame_lock:
            if self.current_frame is None:
                logger.warning("No current frame available")
                return {
                    "success": False,
                    "message": "No frame available",
                    "frame_path": None,
                    "timestamp": None,
                    "detection_data": {}
                }
            
            # Get detection data for current frame
            detection_data = {}
            if self.current_raw_frame is not None:
                # Run detections on current frame
                faces = self._detect_faces(self.current_raw_frame)
                materials = self._detect_reading_material(self.current_raw_frame)
                
                # Calculate positioning and guidance data
                img_height, img_width = self.current_raw_frame.shape[:2]
                img_center_x = img_width // 2
                img_center_y = img_height // 2
                center_threshold_px = (img_width * 15) // 100  # Default 15% from settings
                
                # Build complete detection data structure
                detection_data = {
                    "reading_materials": materials,
                    "faces": faces,
                    "face_count": len(faces),
                    "positioning": {
                        "img_center_x": img_center_x,
                        "img_center_y": img_center_y,
                        "frame_width": img_width,
                        "frame_height": img_height,
                        "center_threshold_px": center_threshold_px,
                        "center_threshold_percent": 15
                    },
                    "robot_guidance": {},
                    "session_info": {
                        "session_id": self.session_id,
                        "session_active": self.session_active,
                        "timestamp": self.last_processed_time,
                        "datetime": datetime.fromtimestamp(self.last_processed_time).strftime("%Y-%m-%d_%H%M%S_%f")[:-3] if self.last_processed_time else None,
                        "filename": os.path.basename(self.preview_file)
                    }
                }
                
                # Calculate robot guidance for reading materials
                if materials:
                    material = materials[0]  # Use first detected material
                    bbox_center_x = material.get("bbox_center_x", img_center_x)
                    bbox_center_y = material.get("bbox_center_y", img_center_y)
                    
                    arrow_dx = img_center_x - bbox_center_x
                    arrow_dy = img_center_y - bbox_center_y
                    movement_magnitude = math.sqrt(arrow_dx**2 + arrow_dy**2)
                    
                    # Determine robot command
                    direction = ""
                    if arrow_dx > 0:
                        direction += "RIGHT"
                    elif arrow_dx < 0:
                        direction += "LEFT"
                    if arrow_dy > 0:
                        direction += "_DOWN" if direction else "DOWN"
                    elif arrow_dy < 0:
                        direction += "_UP" if direction else "UP"
                        
                    robot_command = f"MOVE_{direction}" if direction else "CENTERED"
                    
                    detection_data["robot_guidance"] = {
                        "arrow_dx": arrow_dx,
                        "arrow_dy": arrow_dy,
                        "movement_magnitude": movement_magnitude,
                        "robot_command": robot_command
                    }
                    
                    detection_data["positioning"]["distance_from_center"] = movement_magnitude
            
            return {
                "success": True,
                "message": "Current frame and detection data retrieved",
                "frame_path": self.preview_file,
                "timestamp": self.last_processed_time,
                "detection_data": detection_data
            }
    
    def _get_captured_images(self):
        """Get the list of images captured in the current or last session."""
        # Create a summary file with session information if there are images
        if self.captured_images and self.session_dir:
            try:
                # Create a simple summary text file
                summary_path = os.path.join(self.session_dir, "session_info.txt")
                with open(summary_path, "w") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"Session ID: {self.session_id}\n")
                    f.write(f"Recorded on: {timestamp}\n")
                    f.write(f"Total images: {len(self.captured_images)}\n\n")
                    
                    # Add detection models information
                    f.write("Detection Models:\n")
                    f.write(f"  Face Detection: {'Enabled' if self.face_detection_enabled else 'Disabled'}\n")
                    f.write(f"  Reading Material Detection: {'Enabled' if self.reading_material_detection_enabled else 'Disabled'}\n")
                    if self.reading_material_detection_enabled and self.model_type:
                        f.write(f"  Model Type: {self.model_type.upper()}{' (NCNN)' if self.use_ncnn and self.model_type == 'ncnn' else ''}\n\n")
                    
                    for i, img in enumerate(self.captured_images, 1):
                        date_str = img.get("datetime", "")
                        f.write(f"Image {i}: {os.path.basename(img['filename'])} - {date_str}\n")
                        
                logger.info(f"Created session summary at {summary_path}")
            except Exception as e:
                logger.error(f"Error creating session summary: {e}")
        
        return {
            "success": True,
            "message": f"Retrieved {len(self.captured_images)} captured images",
            "session_data": {
                "session_id": self.session_id,
                "session_dir": self.session_dir,
                "images": self.captured_images,
                "detection_status": self._get_detection_status()
            }
        }