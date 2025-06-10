#!/usr/bin/env python3
"""
Camera Tool GUI - Enhanced Standalone Interface
===============================================

Advanced GUI interface for the standalone camera tool with:
- Live camera preview with annotations
- Enhanced detection data display
- Robot guidance visualization
- Real-time status monitoring

Based on AIDB camera tool implementation with fidelity-checked enhancements.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import PIL.Image
import PIL.ImageTk
import os
import json
import threading
import time
import csv
from pathlib import Path

# Import camera tool components
from tools.camera_tool import CameraTool
from utils.settings import Settings
from utils.logging_config import setup_logging

# Set up logging
logger = setup_logging("camera_gui")

class CameraToolGUI:
    """
    Enhanced GUI for the camera tool with rich detection data display
    Following AIDB patterns with enhanced visualization capabilities
    """
    
    def __init__(self, root):
        """Initialize the GUI - following AIDB main.py GUI pattern"""
        self.root = root
        self.root.title("Camera Detection Tool - Enhanced Data Display")
        self.root.geometry("1200x800")
        
        # Initialize settings
        self.settings = Settings()
        
        # Initialize camera tool
        self.camera_tool = CameraTool(settings=self.settings, tool_name="camera_tool")
        self.camera_tool.set_callbacks(
            on_image_captured=self.on_image_captured,
            on_frame_captured=self.on_preview_frame_captured
        )
        
        # Initialize state
        self.camera_running = False
        self.session_active = False
        self.current_preview_image = None
        self.detection_data = {}
        
        # Create GUI components
        self.create_gui()
        
        # Start update loop
        self.update_loop()
        
        # Add a startup message to CLI history
        self.add_startup_message_to_history()
        
        # Add some demo detection events for immediate visibility
        self.add_demo_detection_events()
        
        logger.info("Camera GUI initialized successfully")
        
    def create_gui(self):
        """Create the main GUI layout"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create control panel
        self.create_control_panel(main_container)
        
        # Create main content area with camera and detection data
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Left side - Camera preview
        self.create_camera_preview(content_frame)
        
        # Right side - Detection data display
        self.create_detection_display(content_frame)
        
        # Bottom status bar
        self.create_status_bar(main_container)
        
    def create_control_panel(self, parent):
        """Create enhanced control panel with buttons"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Session controls
        session_frame = ttk.LabelFrame(control_frame, text="Session Control")
        session_frame.pack(side="left", padx=(0, 10))
        
        self.start_session_btn = ttk.Button(
            session_frame, 
            text="Start Session", 
            command=self.start_session,
            state="disabled"
        )
        self.start_session_btn.pack(side="left", padx=5, pady=5)
        
        self.end_session_btn = ttk.Button(
            session_frame, 
            text="End Session", 
            command=self.end_session,
            state="disabled"
        )
        self.end_session_btn.pack(side="left", padx=5, pady=5)
        
        # Camera controls
        camera_frame = ttk.LabelFrame(control_frame, text="Camera Control")
        camera_frame.pack(side="left", padx=(0, 10))
        
        self.start_camera_btn = ttk.Button(
            camera_frame, 
            text="Start Camera", 
            command=self.start_camera
        )
        self.start_camera_btn.pack(side="left", padx=5, pady=5)
        
        self.stop_camera_btn = ttk.Button(
            camera_frame, 
            text="Stop Camera", 
            command=self.stop_camera,
            state="disabled"
        )
        self.stop_camera_btn.pack(side="left", padx=5, pady=5)
        
        # Frame rate controls - NEW FEATURE
        frame_rate_frame = ttk.LabelFrame(control_frame, text="Frame Rate")
        frame_rate_frame.pack(side="left", padx=(0, 10))
        
        ttk.Label(frame_rate_frame, text="Interval:").pack(side="left", padx=5)
        self.frame_rate_var = tk.StringVar(value="1.0s")
        self.frame_rate_combo = ttk.Combobox(
            frame_rate_frame, 
            textvariable=self.frame_rate_var,
            values=["0.5s per image", "1.0s per image", "2.0s per image"],
            state="readonly",
            width=12
        )
        self.frame_rate_combo.pack(side="left", padx=5, pady=5)
        self.frame_rate_combo.bind("<<ComboboxSelected>>", self.on_frame_rate_changed)
        
        # Data controls
        data_frame = ttk.LabelFrame(control_frame, text="Data Control")
        data_frame.pack(side="left", padx=(0, 10))
        
        self.get_frame_btn = ttk.Button(
            data_frame, 
            text="Get Frame", 
            command=self.get_current_frame,
            state="disabled"
        )
        self.get_frame_btn.pack(side="left", padx=5, pady=5)
        
        # Auto-update toggle for real-time detection data
        self.auto_update_var = tk.BooleanVar(value=True)  # Start with auto-update enabled
        self.auto_update_checkbox = ttk.Checkbutton(
            data_frame, 
            text="Auto-Update", 
            variable=self.auto_update_var
        )
        self.auto_update_checkbox.pack(side="left", padx=5, pady=5)
        
        self.settings_btn = ttk.Button(
            data_frame, 
            text="Settings", 
            command=self.open_settings
        )
        self.settings_btn.pack(side="left", padx=5, pady=5)
        
        # Initialize frame rate settings
        self.current_frame_interval = 1000  # milliseconds (1 second default)
        
    def create_camera_preview(self, parent):
        """Create camera preview area - following AIDB main.py pattern"""
        # Left panel for camera
        camera_panel = ttk.Frame(parent, width=450)
        camera_panel.pack(side="left", fill="y", padx=(0, 10))
        camera_panel.pack_propagate(False)
        
        # Camera frame (following AIDB exact pattern)
        self.camera_frame = ttk.LabelFrame(camera_panel, text="Live Camera Feed")
        self.camera_frame.pack(fill="both", expand=True)
        
        # Preview container with fixed size (AIDB pattern)
        self.preview_container = ttk.Frame(self.camera_frame, width=400, height=300)
        self.preview_container.pack(pady=10)
        self.preview_container.pack_propagate(False)  # Fixed size
        
        # Preview label for image display
        self.preview_label = ttk.Label(self.preview_container, background="black", text="Camera Preview\n(Start camera to begin)")
        self.preview_label.pack(fill="both", expand=True)
        
        # Camera status
        status_frame = ttk.Frame(camera_panel)
        status_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.camera_status = ttk.Label(status_frame, text="Camera inactive", foreground="red")
        self.camera_status.pack(side="left", padx=(5, 0))
        
        ttk.Label(status_frame, text="Session:").pack(side="left", padx=(20, 0))
        self.recording_status = ttk.Label(status_frame, text="inactive", foreground="gray")
        self.recording_status.pack(side="left", padx=(5, 0))
        
    def create_detection_display(self, parent):
        """Create unified detection data display panel - like CLI but readable"""
        # Right panel for detection data
        detection_panel = ttk.Frame(parent)
        detection_panel.pack(side="left", fill="both", expand=True)
        
        # Detection data frame
        self.detection_frame = ttk.LabelFrame(detection_panel, text="Detection Data")
        self.detection_frame.pack(fill="both", expand=True)
        
        # Create single unified display (no tabs)
        self.create_unified_detection_display(self.detection_frame)
        
    def create_unified_detection_display(self, parent):
        """Create unified detection display showing all data like CLI but readable"""
        # Main container with scrolling
        main_container = ttk.Frame(parent)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # === READING MATERIALS SECTION ===
        materials_frame = ttk.LabelFrame(main_container, text="📖 Reading Materials")
        materials_frame.pack(fill="x", pady=(0, 5))
        
        # Materials header with count
        materials_header = ttk.Frame(materials_frame)
        materials_header.pack(fill="x", padx=5, pady=2)
        
        self.materials_count_label = ttk.Label(materials_header, text="Reading Materials: 0", 
                                               font=("Arial", 10, "bold"), foreground="blue")
        self.materials_count_label.pack(side="left")
        
        # Materials details
        self.materials_details = tk.Text(materials_frame, height=6, wrap=tk.WORD)
        self.materials_details.pack(fill="x", padx=5, pady=2)
        
        # === FACES SECTION ===
        faces_frame = ttk.LabelFrame(main_container, text="👤 Faces Detected")
        faces_frame.pack(fill="x", pady=(0, 5))
        
        # Faces header with count
        faces_header = ttk.Frame(faces_frame)
        faces_header.pack(fill="x", padx=5, pady=2)
        
        self.faces_count_label = ttk.Label(faces_header, text="Faces Detected: 0", 
                                           font=("Arial", 10, "bold"), foreground="purple")
        self.faces_count_label.pack(side="left")
        
        # Faces details
        self.faces_details = tk.Text(faces_frame, height=4, wrap=tk.WORD)
        self.faces_details.pack(fill="x", padx=5, pady=2)
        
        # === ROBOT GUIDANCE SECTION ===
        guidance_frame = ttk.LabelFrame(main_container, text="🤖 Robot Guidance")
        guidance_frame.pack(fill="x", pady=(0, 5))
        
        # Guidance details
        self.guidance_details = tk.Text(guidance_frame, height=4, wrap=tk.WORD)
        self.guidance_details.pack(fill="x", padx=5, pady=5)
        
        # === SESSION INFO SECTION ===
        session_frame = ttk.LabelFrame(main_container, text="📊 Session Info")
        session_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        # Create enhanced session display with CLI-style history
        self.create_session_display(session_frame)
        
        # Create a dummy session_details widget for compatibility with formatting functions
        self.session_details = tk.Text(session_frame, height=1)
        self.session_details.pack_forget()  # Hide it since we're using the enhanced display
        
        # Configure text widgets as read-only with better colors
        for widget in [self.materials_details, self.faces_details, self.guidance_details]:
            widget.configure(state='disabled', bg='#f8f8f8', fg='#333333')
        
    def create_materials_display(self, parent):
        """Create enhanced reading materials detection display with progress bars"""
        # Materials count and status
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(status_frame, text="Reading Materials:").pack(side="left")
        self.materials_count_label = ttk.Label(status_frame, text="0", foreground="blue", font=("Arial", 12, "bold"))
        self.materials_count_label.pack(side="left", padx=(5, 0))
        
        # Export button
        self.export_materials_btn = ttk.Button(status_frame, text="Export Data", command=lambda: self.export_data("materials"))
        self.export_materials_btn.pack(side="right")
        
        # Detection details with progress bars
        details_frame = ttk.Frame(parent)
        details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollable frame for materials
        canvas = tk.Canvas(details_frame, height=200)
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=canvas.yview)
        self.materials_scrollable_frame = ttk.Frame(canvas)
        
        self.materials_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.materials_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for updates
        self.materials_canvas = canvas
        self.materials_widgets = []
        
    def create_faces_display(self, parent):
        """Create enhanced face detection display with visualization"""
        # Face count and status
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(status_frame, text="Faces Detected:").pack(side="left")
        self.faces_count_label = ttk.Label(status_frame, text="0", foreground="purple", font=("Arial", 12, "bold"))
        self.faces_count_label.pack(side="left", padx=(5, 0))
        
        # Face size indicator
        ttk.Label(status_frame, text="Avg Size:").pack(side="left", padx=(20, 0))
        self.face_size_label = ttk.Label(status_frame, text="N/A")
        self.face_size_label.pack(side="left", padx=(5, 0))
        
        # Export button
        self.export_faces_btn = ttk.Button(status_frame, text="Export Data", command=lambda: self.export_data("faces"))
        self.export_faces_btn.pack(side="right")
        
        # Face details
        details_frame = ttk.Frame(parent)
        details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollable frame for faces
        canvas = tk.Canvas(details_frame, height=200)
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=canvas.yview)
        self.faces_scrollable_frame = ttk.Frame(canvas)
        
        self.faces_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.faces_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store references
        self.faces_canvas = canvas
        self.faces_widgets = []
        
    def create_guidance_display(self, parent):
        """Create enhanced robot guidance display with visual indicators"""
        # Movement status
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(status_frame, text="Robot Command:").pack(side="left")
        self.robot_command_label = ttk.Label(status_frame, text="NONE", foreground="gray", font=("Arial", 10, "bold"))
        self.robot_command_label.pack(side="left", padx=(5, 0))
        
        # Export button
        self.export_guidance_btn = ttk.Button(status_frame, text="Export Data", command=lambda: self.export_data("guidance"))
        self.export_guidance_btn.pack(side="right")
        
        # Movement visualization
        movement_frame = ttk.LabelFrame(parent, text="Movement Visualization")
        movement_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Canvas for movement arrows
        self.movement_canvas = tk.Canvas(movement_frame, height=150, bg="white")
        self.movement_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Movement magnitude progress bar
        magnitude_frame = ttk.Frame(parent)
        magnitude_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(magnitude_frame, text="Movement Magnitude:").pack(side="left")
        self.magnitude_progress = ttk.Progressbar(magnitude_frame, length=200, mode="determinate")
        self.magnitude_progress.pack(side="left", padx=(5, 0), fill="x", expand=True)
        
        self.magnitude_label = ttk.Label(magnitude_frame, text="0 px")
        self.magnitude_label.pack(side="right")
        
        # Initialize movement visualization
        self.draw_movement_indicator(0, 0, 0)
        
    def create_session_display(self, parent):
        """Create enhanced session info display with metrics"""
        # Session overview
        overview_frame = ttk.Frame(parent)
        overview_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(overview_frame, text="Session ID:").pack(side="left")
        self.session_id_label = ttk.Label(overview_frame, text="None", foreground="blue")
        self.session_id_label.pack(side="left", padx=(5, 0))
        
        # Export button
        self.export_session_btn = ttk.Button(overview_frame, text="Export Data", command=lambda: self.export_data("session"))
        self.export_session_btn.pack(side="right")
        
        # Performance metrics
        metrics_frame = ttk.LabelFrame(parent, text="Performance Metrics")
        metrics_frame.pack(fill="x", padx=5, pady=5)
        
        # FPS display
        fps_frame = ttk.Frame(metrics_frame)
        fps_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(fps_frame, text="Detection FPS:").pack(side="left")
        self.fps_label = ttk.Label(fps_frame, text="0.0", foreground="green", font=("Arial", 10, "bold"))
        self.fps_label.pack(side="left", padx=(5, 0))
        
        # Average inference time
        inference_frame = ttk.Frame(metrics_frame)
        inference_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(inference_frame, text="Avg Inference:").pack(side="left")
        self.inference_label = ttk.Label(inference_frame, text="0ms", foreground="orange")
        self.inference_label.pack(side="left", padx=(5, 0))
        
        # Enhanced Detection History - CLI-style
        history_frame = ttk.LabelFrame(parent, text="Detection History (CLI-style)")
        history_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # History display using Text widget for better formatting
        history_display_frame = ttk.Frame(history_frame)
        history_display_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.history_text = tk.Text(
            history_display_frame, 
            height=12, 
            wrap=tk.WORD, 
            bg='#1e1e1e',  # Dark background like CLI
            fg='#00ff00',  # Green text like CLI
            font=('Courier', 10),  # Monospace font
            state='disabled'
        )
        history_v_scroll = ttk.Scrollbar(history_display_frame, orient="vertical", command=self.history_text.yview)
        history_h_scroll = ttk.Scrollbar(history_display_frame, orient="horizontal", command=self.history_text.xview)
        self.history_text.configure(yscrollcommand=history_v_scroll.set, xscrollcommand=history_h_scroll.set)
        
        self.history_text.pack(side="left", fill="both", expand=True)
        history_v_scroll.pack(side="right", fill="y")
        history_h_scroll.pack(side="bottom", fill="x")
        
        # History controls
        history_controls = ttk.Frame(history_frame)
        history_controls.pack(fill="x", padx=5, pady=2)
        
        self.clear_history_btn = ttk.Button(history_controls, text="Clear History", command=self.clear_detection_history)
        self.clear_history_btn.pack(side="left")
        
        # History settings
        self.history_verbose_var = tk.BooleanVar(value=True)
        self.history_verbose_checkbox = ttk.Checkbutton(
            history_controls, 
            text="Verbose Mode", 
            variable=self.history_verbose_var
        )
        self.history_verbose_checkbox.pack(side="left", padx=(10, 0))
        
        # Auto-scroll toggle
        self.history_autoscroll_var = tk.BooleanVar(value=True)
        self.history_autoscroll_checkbox = ttk.Checkbutton(
            history_controls, 
            text="Auto-scroll", 
            variable=self.history_autoscroll_var
        )
        self.history_autoscroll_checkbox.pack(side="left", padx=(10, 0))
        
        # Initialize performance tracking
        self.detection_history = []
        self.performance_times = []
        
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready - Start camera to begin detection")
        self.status_label.pack(side="left")
        
        # Activity indicator
        self.activity_var = tk.StringVar(value="●")
        self.activity_label = ttk.Label(status_frame, textvariable=self.activity_var, foreground="gray")
        self.activity_label.pack(side="right")
        
    # === CAMERA CONTROL METHODS ===
    
    def start_camera(self):
        """Start camera system"""
        try:
            # Initialize camera tool
            if not self.camera_tool.initialize_tool():
                self.update_status("Failed to initialize camera tool", "error")
                return
                
            # Start camera
            result = self.camera_tool.process_command("start_camera", {})
            if result.get("success", False):
                self.camera_running = True
                self.update_status("Camera started successfully", "success")
                self.camera_status.config(text="Camera active", foreground="green")
                
                # Update button states
                self.start_camera_btn.config(state="disabled")
                self.stop_camera_btn.config(state="normal")
                self.start_session_btn.config(state="normal")
                self.get_frame_btn.config(state="normal")
            else:
                self.update_status(f"Failed to start camera: {result.get('message', 'Unknown error')}", "error")
                
        except Exception as e:
            logger.exception(f"Error starting camera: {e}")
            self.update_status(f"Error starting camera: {e}", "error")
            
    def stop_camera(self):
        """Stop camera system"""
        try:
            # End session if active
            if self.session_active:
                self.end_session()
                
            # Stop camera
            result = self.camera_tool.process_command("stop_camera", {})
            if result.get("success", False):
                self.camera_running = False
                self.update_status("Camera stopped", "info")
                self.camera_status.config(text="Camera inactive", foreground="red")
                
                # Clear preview
                self.preview_label.config(image="", text="Camera Preview\n(Start camera to begin)")
                self.current_preview_image = None
                
                # Update button states
                self.start_camera_btn.config(state="normal")
                self.stop_camera_btn.config(state="disabled")
                self.start_session_btn.config(state="disabled")
                self.end_session_btn.config(state="disabled")
                self.get_frame_btn.config(state="disabled")
            else:
                self.update_status(f"Failed to stop camera: {result.get('message', 'Unknown error')}", "error")
                
        except Exception as e:
            logger.exception(f"Error stopping camera: {e}")
            self.update_status(f"Error stopping camera: {e}", "error")
            
    def start_session(self):
        """Start camera session"""
        try:
            result = self.camera_tool.process_command("start_session", {})
            if result.get("success", False):
                self.session_active = True
                session_info = result.get("session_info", {})
                session_id = session_info.get("session_id", "unknown")
                
                self.update_status(f"Session started: {session_id}", "success")
                self.recording_status.config(text="active", foreground="green")
                
                # Update button states
                self.start_session_btn.config(state="disabled")
                self.end_session_btn.config(state="normal")
            else:
                self.update_status(f"Failed to start session: {result.get('message', 'Unknown error')}", "error")
                
        except Exception as e:
            logger.exception(f"Error starting session: {e}")
            self.update_status(f"Error starting session: {e}", "error")
            
    def end_session(self):
        """End camera session"""
        try:
            result = self.camera_tool.process_command("end_session", {})
            if result.get("success", False):
                self.session_active = False
                session_data = result.get("session_data", {})
                images_count = len(session_data.get("images", []))
                
                self.update_status(f"Session ended - {images_count} images captured", "success")
                self.recording_status.config(text="inactive", foreground="gray")
                
                # Update button states
                self.start_session_btn.config(state="normal")
                self.end_session_btn.config(state="disabled")
            else:
                self.update_status(f"Failed to end session: {result.get('message', 'Unknown error')}", "error")
                
        except Exception as e:
            logger.exception(f"Error ending session: {e}")
            self.update_status(f"Error ending session: {e}", "error")
            
    def get_current_frame(self):
        """Get current frame and detection data"""
        try:
            result = self.camera_tool.process_command("get_current_frame", {})
            if result.get("success", False):
                frame_path = result.get("frame_path")
                if frame_path and os.path.exists(frame_path):
                    # Update preview
                    self.on_preview_frame_captured(frame_path)
                    
                    # Get detection data from frame result
                    self.detection_data = result.get("detection_data", {})
                    self.update_detection_displays()
                    
                    self.update_status("Frame and detection data updated", "success")
                else:
                    self.update_status("No frame available", "warning")
            else:
                self.update_status(f"Failed to get frame: {result.get('message', 'Unknown error')}", "error")
                
        except Exception as e:
            logger.exception(f"Error getting frame: {e}")
            self.update_status(f"Error getting frame: {e}", "error")
            
    def open_settings(self):
        """Open enhanced settings dialog"""
        self.create_settings_dialog()
        
    # === CALLBACK METHODS ===
    
    def on_image_captured(self, image_path):
        """Handle session image capture"""
        logger.info(f"Session image captured: {image_path}")
        self.update_status(f"Image saved: {os.path.basename(image_path)}", "info")
        
    def on_preview_frame_captured(self, frame_path):
        """Handle preview frame update - following AIDB main.py pattern"""
        if os.path.exists(frame_path):
            try:
                # Load and resize image maintaining aspect ratio (AIDB pattern)
                image = PIL.Image.open(frame_path)
                display_width, display_height = 400, 300
                img_width, img_height = image.size
                aspect = img_width / img_height
                
                if aspect > (display_width / display_height):
                    new_width = display_width
                    new_height = int(display_width / aspect)
                else:
                    new_height = display_height
                    new_width = int(display_height * aspect)
                
                image = image.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)
                self.current_preview_image = PIL.ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.current_preview_image, text="")
                
                # Update activity indicator
                self.activity_var.set("●" if self.activity_var.get() == "○" else "○")
                
            except Exception as e:
                logger.exception(f"Error updating preview: {e}")
                
    def update_detection_displays(self):
        """Update unified detection display with rich, readable data"""
        print(f"DEBUG: detection_data = {self.detection_data}")  # DEBUG LINE
        if not self.detection_data:
            print("DEBUG: No detection data available")  # DEBUG LINE
            return
            
        try:
            # Update Reading Materials
            materials = self.detection_data.get("reading_materials", [])
            materials_count = len(materials)
            self.materials_count_label.config(text=f"Reading Materials: {materials_count}")
            self.materials_count_label.config(foreground="green" if materials_count > 0 else "gray")
            
            materials_text = self.format_materials_data_unified(materials)
            self.update_text_widget(self.materials_details, materials_text)
            
            # Update Faces
            faces = self.detection_data.get("faces", [])
            face_count = self.detection_data.get("face_count", 0)
            self.faces_count_label.config(text=f"Faces Detected: {face_count}")
            self.faces_count_label.config(foreground="purple" if face_count > 0 else "gray")
            
            faces_text = self.format_faces_data_unified(faces, face_count)
            self.update_text_widget(self.faces_details, faces_text)
            
            # Update Robot Guidance
            guidance = self.detection_data.get("robot_guidance", {})
            positioning = self.detection_data.get("positioning", {})
            guidance_text = self.format_guidance_data_unified(guidance, positioning)
            self.update_text_widget(self.guidance_details, guidance_text)
            
            # Update Session Info
            session_info = self.detection_data.get("session_info", {})
            session_text = self.format_session_data_unified(session_info, self.detection_data)
            self.update_text_widget(self.session_details, session_text)
            
        except Exception as e:
            logger.exception(f"Error updating detection displays: {e}")
    
    def format_materials_data_unified(self, materials):
        """Format reading materials data for unified display - like CLI but readable"""
        if not materials:
            return "🔍 No reading materials detected"
            
        text = f"📖 {len(materials)} reading material{'s' if len(materials) > 1 else ''} detected:\n\n"
        
        for i, material in enumerate(materials, 1):
            box = material.get("box", [0, 0, 0, 0])
            confidence = material.get("confidence", 0)
            
            text += f"Material {i}:\n"
            text += f"  🎯 Confidence: {confidence:.1%} ({confidence:.3f})\n"
            text += f"  📍 Bounding Box: [{box[0]}, {box[1]}, {box[2]}, {box[3]}]\n"
            text += f"  📏 Position: ({box[0]}, {box[1]})  Size: {box[2]}×{box[3]} px\n"
            
            # Calculate center
            center_x = box[0] + box[2] // 2
            center_y = box[1] + box[3] // 2
            text += f"  🎯 Center: ({center_x}, {center_y})\n"
            
            # Check if multiple materials
            if i < len(materials):
                text += "\n"
                
        return text
    
    def format_faces_data_unified(self, faces, face_count):
        """Format face detection data for unified display"""
        if face_count == 0:
            return "👤 No faces detected"
            
        text = f"👥 {face_count} face{'s' if face_count != 1 else ''} detected:\n\n"
        
        # Handle different face data formats
        if hasattr(faces, 'shape'):  # NumPy array
            for i, face in enumerate(faces):
                x, y, w, h = face
                text += f"Face {i+1}:\n"
                text += f"  📍 Position: ({x}, {y})\n"
                text += f"  📏 Size: {w}×{h} pixels\n"
                text += f"  🎯 Center: ({x + w//2}, {y + h//2})\n"
                if i < len(faces) - 1:
                    text += "\n"
        elif isinstance(faces, list):  # List format
            for i, face in enumerate(faces):
                if isinstance(face, dict):
                    box = face.get("box", [0, 0, 0, 0])
                    text += f"Face {i+1}:\n"
                    text += f"  📍 Box: [{box[0]}, {box[1]}, {box[2]}, {box[3]}]\n"
                    if i < len(faces) - 1:
                        text += "\n"
                        
        return text
    
    def format_guidance_data_unified(self, guidance, positioning):
        """Format robot guidance data for unified display"""
        if not guidance:
            text = "🤖 No movement guidance available\n\n"
        else:
            # Movement commands
            arrow_dx = guidance.get("arrow_dx", 0)
            arrow_dy = guidance.get("arrow_dy", 0)
            magnitude = guidance.get("movement_magnitude", 0)
            command = guidance.get("robot_command", "UNKNOWN")
            
            text = f"🎯 Command: {command}\n"
            text += f"➡️  Horizontal: {arrow_dx:+.0f} px\n"
            text += f"⬇️  Vertical: {arrow_dy:+.0f} px\n"
            text += f"📏 Magnitude: {magnitude:.1f} px\n\n"
        
        # Positioning information - always show if available
        if positioning:
            text += "📐 Frame Positioning:\n"
            text += f"  🖼️  Frame: {positioning.get('frame_width', 0)}×{positioning.get('frame_height', 0)} px\n"
            text += f"  🎯 Center: ({positioning.get('img_center_x', 0)}, {positioning.get('img_center_y', 0)})\n"
            text += f"  📏 Threshold: {positioning.get('center_threshold_px', 0)} px ({positioning.get('center_threshold_percent', 0)}%)\n"
            
            distance = positioning.get('distance_from_center', 0)
            text += f"  📍 Distance from center: {distance:.1f} px\n"
            
        return text
    
    def format_session_data_unified(self, session_info, detection_data):
        """Format session data for unified display"""
        text = ""
        
        if session_info:
            # Concise session details
            session_id = session_info.get('session_id', 'Unknown')
            active = session_info.get('session_active', False)
            time = session_info.get('datetime', 'Unknown')
            
            text += f"🆔 Session: {session_id}\n"
            text += f"▶️  Status: {'✅ Active' if active else '❌ Inactive'}\n"
            text += f"⏰ Time: {time}\n\n"
        
        # Live performance metrics
        materials_count = len(detection_data.get("reading_materials", []))
        face_count = detection_data.get("face_count", 0)
        
        text += "⚡ Live Performance:\n"
        text += f"  📖 Materials: {materials_count}\n"
        text += f"  👤 Faces: {face_count}\n"
        
        # Auto-update status
        auto_update = getattr(self, 'auto_update_var', None)
        if auto_update:
            text += f"  🔄 Auto-update: {'✅ ON' if auto_update.get() else '❌ OFF'}\n"
        
        text += f"  📊 Update Rate: ~2 FPS (500ms)\n"
        
        return text
        
    def format_materials_data(self, data):
        """Format reading materials data for display"""
        materials = data.get("reading_materials", [])
        if not materials:
            return "No reading materials detected"
            
        text = f"Reading Materials Detected: {len(materials)}\n\n"
        for i, material in enumerate(materials, 1):
            box = material.get("box", [0, 0, 0, 0])
            confidence = material.get("confidence", 0)
            centered = material.get("is_centered", False)
            center_x = material.get("bbox_center_x", 0)
            center_y = material.get("bbox_center_y", 0)
            
            text += f"Material {i}:\n"
            text += f"  • Box: [{box[0]}, {box[1]}, {box[2]}, {box[3]}]\n"
            text += f"  • Confidence: {confidence:.1%}\n"
            text += f"  • Center: ({center_x}, {center_y})\n"
            text += f"  • Centered: {'Yes' if centered else 'No'}\n\n"
            
        return text
        
    def format_faces_data(self, data):
        """Format face detection data for display"""
        faces = data.get("faces", [])
        face_count = data.get("face_count", 0)
        
        if face_count == 0:
            return "No faces detected"
            
        text = f"Faces Detected: {face_count}\n\n"
        for face in faces:
            box = face.get("box", [0, 0, 0, 0])
            face_id = face.get("face_id", 0)
            
            text += f"Face {face_id}:\n"
            text += f"  • Box: [{box[0]}, {box[1]}, {box[2]}, {box[3]}]\n"
            text += f"  • Size: {box[2]}x{box[3]} pixels\n\n"
            
        return text
        
    def format_guidance_data(self, data):
        """Format robot guidance data for display"""
        guidance = data.get("robot_guidance", {})
        positioning = data.get("positioning", {})
        
        if not guidance:
            return "No robot guidance data available"
            
        text = "Robot Guidance:\n\n"
        text += f"Movement Direction:\n"
        text += f"  • Right: {guidance.get('arrow_dx', 0)} pixels\n"
        text += f"  • Down: {guidance.get('arrow_dy', 0)} pixels\n"
        text += f"  • Magnitude: {guidance.get('movement_magnitude', 0):.1f} pixels\n"
        text += f"  • Command: {guidance.get('robot_command', 'UNKNOWN')}\n\n"
        
        text += f"Positioning Data:\n"
        text += f"  • Frame Size: {positioning.get('frame_width', 0)}x{positioning.get('frame_height', 0)}\n"
        text += f"  • Center: ({positioning.get('img_center_x', 0)}, {positioning.get('img_center_y', 0)})\n"
        text += f"  • Distance from Center: {positioning.get('distance_from_center', 0):.1f} pixels\n"
        text += f"  • Center Threshold: {positioning.get('center_threshold_px', 0)} pixels\n"
        
        return text
        
    def format_session_data(self, data):
        """Format session data for display"""
        session_info = data.get("session_info", {})
        
        if not session_info:
            return "No session data available"
            
        text = "Session Information:\n\n"
        text += f"Session ID: {session_info.get('session_id', 'Unknown')}\n"
        text += f"Active: {'Yes' if session_info.get('session_active', False) else 'No'}\n"
        text += f"Timestamp: {session_info.get('timestamp', 'Unknown')}\n"
        text += f"DateTime: {session_info.get('datetime', 'Unknown')}\n"
        text += f"Filename: {session_info.get('filename', 'Unknown')}\n"
        
        return text
        
    def update_text_widget(self, widget, text):
        """Update text widget content"""
        widget.config(state="normal")
        widget.delete(1.0, tk.END)
        widget.insert(1.0, text)
        widget.config(state="disabled")
        
    def update_status(self, message, level="info"):
        """Update status bar message"""
        colors = {
            "info": "black",
            "success": "green",
            "warning": "orange", 
            "error": "red"
        }
        
        self.status_label.config(text=message, foreground=colors.get(level, "black"))
        logger.info(f"Status: {message}")
        
    def update_loop(self):
        """Main update loop for GUI - Real-time detection data updates with configurable frame rate"""
        try:
            if self.camera_running and self.auto_update_var.get():
                # Get current frame and detection data automatically
                result = self.camera_tool.process_command("get_current_frame", {})
                if result.get("success", False):
                    # Update detection data from frame result
                    self.detection_data = result.get("detection_data", {})
                    self.update_detection_displays()
                    
                    # Update preview if available
                    frame_path = result.get("frame_path")
                    if frame_path and os.path.exists(frame_path):
                        self.on_preview_frame_captured(frame_path)
                    
                    # Add to detection history
                    self.add_to_detection_history(self.detection_data)
                    
                    # Update activity indicator
                    self.activity_var.set("●" if self.detection_data.get("reading_materials") else "○")
                    self.activity_label.config(foreground="green" if self.detection_data.get("reading_materials") else "gray")
                    
        except Exception as e:
            logger.exception(f"Error in update loop: {e}")
            
        # Schedule next update using configurable frame interval
        self.root.after(self.current_frame_interval, self.update_loop)
        
    # === ENHANCED VISUALIZATION METHODS (Phase 2) ===
    
    def update_materials_display_enhanced(self, data):
        """Update reading materials display with enhanced visualization"""
        materials = data.get("reading_materials", [])
        
        # Update count
        count = len(materials)
        self.materials_count_label.config(text=str(count))
        self.materials_count_label.config(foreground="green" if count > 0 else "gray")
        
        # Clear existing widgets
        for widget in self.materials_widgets:
            widget.destroy()
        self.materials_widgets.clear()
        
        # Create enhanced material displays
        for i, material in enumerate(materials):
            material_frame = ttk.LabelFrame(self.materials_scrollable_frame, text=f"Material {i+1}")
            material_frame.pack(fill="x", padx=5, pady=2)
            self.materials_widgets.append(material_frame)
            
            # Confidence progress bar
            conf_frame = ttk.Frame(material_frame)
            conf_frame.pack(fill="x", padx=5, pady=2)
            
            ttk.Label(conf_frame, text="Confidence:").pack(side="left")
            confidence = material.get("confidence", 0)
            
            conf_progress = ttk.Progressbar(conf_frame, length=100, mode="determinate")
            conf_progress["value"] = confidence * 100
            conf_progress.pack(side="left", padx=(5, 0))
            
            conf_label = ttk.Label(conf_frame, text=f"{confidence:.1%}")
            conf_label.pack(side="left", padx=(5, 0))
            
            # Position and centering info
            info_frame = ttk.Frame(material_frame)
            info_frame.pack(fill="x", padx=5, pady=2)
            
            box = material.get("box", [0, 0, 0, 0])
            centered = material.get("is_centered", False)
            
            ttk.Label(info_frame, text=f"Position: ({box[0]}, {box[1]})").pack(side="left")
            ttk.Label(info_frame, text=f"Size: {box[2]}x{box[3]}").pack(side="left", padx=(10, 0))
            
            center_label = ttk.Label(info_frame, text="CENTERED" if centered else "NOT CENTERED")
            center_label.config(foreground="green" if centered else "red")
            center_label.pack(side="right")
            
    def update_faces_display_enhanced(self, data):
        """Update faces display with enhanced visualization"""
        faces = data.get("faces", [])
        face_count = data.get("face_count", 0)
        
        # Update count
        self.faces_count_label.config(text=str(face_count))
        self.faces_count_label.config(foreground="purple" if face_count > 0 else "gray")
        
        # Calculate average face size
        if faces:
            avg_size = sum(face.get("box", [0, 0, 0, 0])[2] * face.get("box", [0, 0, 0, 0])[3] for face in faces) / len(faces)
            self.face_size_label.config(text=f"{avg_size:.0f}px²")
        else:
            self.face_size_label.config(text="N/A")
            
        # Clear existing widgets
        for widget in self.faces_widgets:
            widget.destroy()
        self.faces_widgets.clear()
        
        # Create enhanced face displays
        for face in faces:
            face_frame = ttk.LabelFrame(self.faces_scrollable_frame, text=f"Face {face.get('face_id', 'Unknown')}")
            face_frame.pack(fill="x", padx=5, pady=2)
            self.faces_widgets.append(face_frame)
            
            box = face.get("box", [0, 0, 0, 0])
            
            # Face info
            info_frame = ttk.Frame(face_frame)
            info_frame.pack(fill="x", padx=5, pady=2)
            
            ttk.Label(info_frame, text=f"Position: ({box[0]}, {box[1]})").pack(side="left")
            ttk.Label(info_frame, text=f"Size: {box[2]}x{box[3]}").pack(side="left", padx=(10, 0))
            
            # Size indicator
            size_area = box[2] * box[3]
            if size_area > 5000:
                size_indicator = "Large"
                color = "green"
            elif size_area > 2000:
                size_indicator = "Medium"
                color = "orange"
            else:
                size_indicator = "Small"
                color = "red"
                
            size_label = ttk.Label(info_frame, text=size_indicator)
            size_label.config(foreground=color)
            size_label.pack(side="right")
            
    def update_guidance_display_enhanced(self, data):
        """Update robot guidance display with visual indicators"""
        guidance = data.get("robot_guidance", {})
        
        if not guidance:
            self.robot_command_label.config(text="NONE", foreground="gray")
            self.magnitude_progress["value"] = 0
            self.magnitude_label.config(text="0 px")
            self.draw_movement_indicator(0, 0, 0)
            return
            
        # Update command label
        command = guidance.get("robot_command", "UNKNOWN")
        self.robot_command_label.config(text=command)
        
        # Color code based on urgency
        magnitude = guidance.get("movement_magnitude", 0)
        if magnitude == 0:
            color = "green"
        elif magnitude < 50:
            color = "blue"
        elif magnitude < 100:
            color = "orange"
        else:
            color = "red"
            
        self.robot_command_label.config(foreground=color)
        
        # Update magnitude progress bar (scale to 200px max)
        max_magnitude = 200
        progress_value = min(magnitude / max_magnitude * 100, 100)
        self.magnitude_progress["value"] = progress_value
        self.magnitude_label.config(text=f"{magnitude:.1f} px")
        
        # Update movement visualization
        arrow_dx = guidance.get("arrow_dx", 0)
        arrow_dy = guidance.get("arrow_dy", 0)
        self.draw_movement_indicator(arrow_dx, arrow_dy, magnitude)
        
    def update_session_display_enhanced(self, data):
        """Update session display with performance metrics"""
        session_info = data.get("session_info", {})
        
        # Update session ID
        session_id = session_info.get("session_id", "None")
        self.session_id_label.config(text=session_id)
        
        # Update performance metrics
        import time
        current_time = time.time()
        self.performance_times.append(current_time)
        
        # Keep only last 10 measurements for FPS calculation
        self.performance_times = self.performance_times[-10:]
        
        if len(self.performance_times) > 1:
            time_diff = self.performance_times[-1] - self.performance_times[0]
            fps = (len(self.performance_times) - 1) / time_diff if time_diff > 0 else 0
            self.fps_label.config(text=f"{fps:.1f}")
            
        # Mock inference time (in real implementation, this would come from detection data)
        self.inference_label.config(text="35ms")  # Based on your terminal output
        
    def add_to_detection_history(self, data):
        """Add detection event to history - Enhanced CLI-style format"""
        import time
        timestamp = time.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        
        materials = data.get("reading_materials", [])
        faces = data.get("faces", [])
        faces_count = data.get("face_count", 0)
        positioning = data.get("positioning", {})
        guidance = data.get("robot_guidance", {})
        
        # Create CLI-style entry
        if self.history_verbose_var.get():
            # Verbose mode - detailed information
            entry = f"[{timestamp}] === DETECTION EVENT ===\n"
            
            # Materials detection
            if materials:
                entry += f"📖 READING MATERIALS: {len(materials)} detected\n"
                for i, material in enumerate(materials):
                    box = material.get("box", [0, 0, 0, 0])
                    conf = material.get("confidence", 0)
                    centered = material.get("is_centered", False)
                    entry += f"  ├─ Material {i+1}: pos=({box[0]},{box[1]}) size=({box[2]}x{box[3]}) conf={conf:.1%} {'✓ CENTERED' if centered else '✗ NOT CENTERED'}\n"
            else:
                entry += f"📖 READING MATERIALS: 0 detected\n"
            
            # Face detection
            if faces_count > 0:
                entry += f"👤 FACES: {faces_count} detected\n"
                for face in faces:
                    box = face.get("box", [0, 0, 0, 0])
                    face_id = face.get("face_id", "?")
                    entry += f"  ├─ Face {face_id}: pos=({box[0]},{box[1]}) size=({box[2]}x{box[3]})\n"
            else:
                entry += f"👤 FACES: 0 detected\n"
            
            # Robot guidance
            if guidance:
                cmd = guidance.get("robot_command", "NONE")
                magnitude = guidance.get("movement_magnitude", 0)
                dx = guidance.get("arrow_dx", 0)
                dy = guidance.get("arrow_dy", 0)
                entry += f"🤖 ROBOT: {cmd} | magnitude={magnitude:.1f}px | vector=({dx},{dy})\n"
            else:
                entry += f"🤖 ROBOT: NO GUIDANCE\n"
            
            # Frame info
            frame_info = positioning
            if frame_info:
                center_x = frame_info.get("img_center_x", 0)
                center_y = frame_info.get("img_center_y", 0)
                entry += f"📷 FRAME: center=({center_x},{center_y}) threshold={frame_info.get('center_threshold_px', 0)}px\n"
            
            entry += "=" * 60 + "\n\n"
        else:
            # Compact mode - one line summary
            materials_count = len(materials)
            robot_cmd = guidance.get("robot_command", "NONE") if guidance else "NONE"
            magnitude = guidance.get("movement_magnitude", 0) if guidance else 0
            
            entry = f"[{timestamp}] M:{materials_count} F:{faces_count} R:{robot_cmd}({magnitude:.0f}px)\n"
        
        # Add to history
        self.detection_history.append(entry)
        
        # Update text widget
        self.history_text.configure(state='normal')
        self.history_text.insert(tk.END, entry)
        self.history_text.configure(state='disabled')
        
        # Keep only last 100 entries (more than before due to enhanced info)
        if len(self.detection_history) > 100:
            self.detection_history.pop(0)
            # Remove first entry from text widget
            self.history_text.configure(state='normal')
            lines = self.history_text.get("1.0", tk.END).split('\n')
            if self.history_verbose_var.get():
                # In verbose mode, each entry is multiple lines, find the first complete entry
                lines_to_remove = 0
                for i, line in enumerate(lines):
                    lines_to_remove += 1
                    if line.startswith("="):  # End of verbose entry
                        lines_to_remove += 1  # Include the empty line after
                        break
                self.history_text.delete("1.0", f"{lines_to_remove}.0")
            else:
                # In compact mode, remove first line
                self.history_text.delete("1.0", "2.0")
            self.history_text.configure(state='disabled')
            
        # Auto-scroll to bottom if enabled
        if self.history_autoscroll_var.get():
            self.history_text.see(tk.END)
        
    def clear_detection_history(self):
        """Clear detection history"""
        self.detection_history.clear()
        self.history_text.configure(state='normal')
        self.history_text.delete(1.0, tk.END)
        self.history_text.configure(state='disabled')
        self.update_status("Detection history cleared", "info")
        
    def draw_movement_indicator(self, dx, dy, magnitude):
        """Draw movement arrow visualization"""
        self.movement_canvas.delete("all")
        
        canvas_width = self.movement_canvas.winfo_width() or 300
        canvas_height = self.movement_canvas.winfo_height() or 150
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Draw center point
        self.movement_canvas.create_oval(center_x-3, center_y-3, center_x+3, center_y+3, fill="blue", outline="blue")
        
        if magnitude == 0:
            # Draw "centered" indicator
            self.movement_canvas.create_text(center_x, center_y-20, text="CENTERED", fill="green", font=("Arial", 12, "bold"))
            return
            
        # Scale arrow to fit canvas
        scale = min(canvas_width, canvas_height) * 0.3 / max(abs(dx), abs(dy), 1)
        arrow_end_x = center_x + dx * scale
        arrow_end_y = center_y + dy * scale
        
        # Draw arrow
        self.movement_canvas.create_line(center_x, center_y, arrow_end_x, arrow_end_y, 
                                       width=3, fill="red", arrow=tk.LAST, arrowshape=(16, 20, 6))
        
        # Draw direction labels
        direction_text = ""
        if dx > 0:
            direction_text += "RIGHT "
        elif dx < 0:
            direction_text += "LEFT "
        if dy > 0:
            direction_text += "DOWN"
        elif dy < 0:
            direction_text += "UP"
            
        self.movement_canvas.create_text(center_x, center_y-30, text=direction_text.strip(), 
                                       fill="red", font=("Arial", 10, "bold"))
        
    def export_data(self, data_type):
        """Export detection data to files"""
        import json
        import csv
        from tkinter import filedialog
        import time
        
        if not self.detection_data:
            self.update_status("No data to export", "warning")
            return
            
        # Ask user for file location
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"camera_detection_{data_type}_{timestamp}"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
            initialvalue=default_filename
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                self.export_to_csv(data_type, file_path)
            else:
                self.export_to_json(data_type, file_path)
                
            self.update_status(f"Data exported to {file_path}", "success")
            
        except Exception as e:
            self.update_status(f"Export failed: {e}", "error")
            
    def export_to_json(self, data_type, file_path):
        """Export data to JSON format"""
        import json
        import time
        
        export_data = {
            "timestamp": time.time(),
            "data_type": data_type,
            "detection_data": self.detection_data,
            "session_active": self.session_active,
            "camera_running": self.camera_running
        }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
    def export_to_csv(self, data_type, file_path):
        """Export data to CSV format"""
        import csv
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            if data_type == "materials":
                writer.writerow(["Material_ID", "Confidence", "X", "Y", "Width", "Height", "Centered"])
                for i, material in enumerate(self.detection_data.get("reading_materials", [])):
                    box = material.get("box", [0, 0, 0, 0])
                    writer.writerow([
                        i+1,
                        material.get("confidence", 0),
                        box[0], box[1], box[2], box[3],
                        material.get("is_centered", False)
                    ])
                    
            elif data_type == "faces":
                writer.writerow(["Face_ID", "X", "Y", "Width", "Height"])
                for face in self.detection_data.get("faces", []):
                    box = face.get("box", [0, 0, 0, 0])
                    writer.writerow([
                        face.get("face_id", 0),
                        box[0], box[1], box[2], box[3]
                    ])
                    
    def create_settings_dialog(self):
        """Create enhanced settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Camera Settings")
        settings_window.geometry("500x400")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Create notebook for organized settings
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Camera settings tab
        camera_tab = ttk.Frame(notebook)
        notebook.add(camera_tab, text="Camera")
        self.create_camera_settings(camera_tab)
        
        # Detection settings tab
        detection_tab = ttk.Frame(notebook)
        notebook.add(detection_tab, text="Detection")
        self.create_detection_settings(detection_tab)
        
        # Performance settings tab
        performance_tab = ttk.Frame(notebook)
        notebook.add(performance_tab, text="Performance")
        self.create_performance_settings(performance_tab)
        
        # Buttons
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(button_frame, text="Apply", command=lambda: self.apply_settings(settings_window)).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side="right")
        
    def create_camera_settings(self, parent):
        """Create camera settings controls"""
        # Camera device
        ttk.Label(parent, text="Camera Device:").pack(anchor="w", padx=5, pady=2)
        self.camera_device_var = tk.StringVar(value=str(self.settings.camera.device_index))
        device_frame = ttk.Frame(parent)
        device_frame.pack(fill="x", padx=5, pady=2)
        ttk.Entry(device_frame, textvariable=self.camera_device_var, width=10).pack(side="left")
        ttk.Label(device_frame, text="(0 for default camera)").pack(side="left", padx=(5, 0))
        
        # Resolution
        ttk.Label(parent, text="Resolution:").pack(anchor="w", padx=5, pady=(10, 2))
        res_frame = ttk.Frame(parent)
        res_frame.pack(fill="x", padx=5, pady=2)
        self.width_var = tk.StringVar(value=str(self.settings.camera.capture_width))
        self.height_var = tk.StringVar(value=str(self.settings.camera.capture_height))
        ttk.Entry(res_frame, textvariable=self.width_var, width=8).pack(side="left")
        ttk.Label(res_frame, text="x").pack(side="left", padx=2)
        ttk.Entry(res_frame, textvariable=self.height_var, width=8).pack(side="left")
        
    def create_detection_settings(self, parent):
        """Create detection settings controls"""
        # Face detection
        self.face_detection_var = tk.BooleanVar(value=self.settings.camera.face_detection_enabled)
        ttk.Checkbutton(parent, text="Enable Face Detection", variable=self.face_detection_var).pack(anchor="w", padx=5, pady=5)
        
        # Reading material detection
        self.material_detection_var = tk.BooleanVar(value=self.settings.camera.reading_material_detection_enabled)
        ttk.Checkbutton(parent, text="Enable Reading Material Detection", variable=self.material_detection_var).pack(anchor="w", padx=5, pady=5)
        
        # Confidence threshold
        ttk.Label(parent, text="Confidence Threshold:").pack(anchor="w", padx=5, pady=(10, 2))
        self.confidence_var = tk.DoubleVar(value=0.5)
        confidence_scale = ttk.Scale(parent, from_=0.1, to=0.9, variable=self.confidence_var, orient="horizontal")
        confidence_scale.pack(fill="x", padx=5, pady=2)
        
    def create_performance_settings(self, parent):
        """Create performance settings controls"""
        # Capture interval
        ttk.Label(parent, text="Capture Interval (seconds):").pack(anchor="w", padx=5, pady=2)
        self.interval_var = tk.DoubleVar(value=1.0)
        interval_scale = ttk.Scale(parent, from_=0.5, to=5.0, variable=self.interval_var, orient="horizontal")
        interval_scale.pack(fill="x", padx=5, pady=2)
        
        # Update frequency
        ttk.Label(parent, text="GUI Update Frequency (seconds):").pack(anchor="w", padx=5, pady=(10, 2))
        self.update_freq_var = tk.DoubleVar(value=2.0)
        update_scale = ttk.Scale(parent, from_=1.0, to=10.0, variable=self.update_freq_var, orient="horizontal")
        update_scale.pack(fill="x", padx=5, pady=2)
        
    def apply_settings(self, settings_window):
        """Apply settings changes"""
        try:
            # Apply camera settings
            self.settings.camera.device_index = int(self.camera_device_var.get())
            self.settings.camera.capture_width = int(self.width_var.get())
            self.settings.camera.capture_height = int(self.height_var.get())
            
            # Apply detection settings
            self.settings.camera.face_detection_enabled = self.face_detection_var.get()
            self.settings.camera.reading_material_detection_enabled = self.material_detection_var.get()
            
            self.update_status("Settings applied successfully", "success")
            settings_window.destroy()
            
        except Exception as e:
            self.update_status(f"Settings apply failed: {e}", "error")

    def on_frame_rate_changed(self, event):
        """Handle frame rate change"""
        selected_interval = self.frame_rate_var.get()
        if selected_interval == "0.5s per image":
            self.current_frame_interval = 500  # milliseconds
        elif selected_interval == "1.0s per image":
            self.current_frame_interval = 1000  # milliseconds
        elif selected_interval == "2.0s per image":
            self.current_frame_interval = 2000  # milliseconds
        else:
            self.current_frame_interval = 1000  # milliseconds (default)

    def add_startup_message_to_history(self):
        """Add a startup message to CLI history"""
        import time
        timestamp = time.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        
        entry = f"[{timestamp}] === STARTUP MESSAGE ===\n"
        entry += "Welcome to the Camera Detection Tool GUI!\n"
        entry += "This is the enhanced standalone interface for the camera tool.\n"
        entry += "You can start capturing images and detecting materials and faces.\n"
        entry += "The GUI will display live camera feed, detection data, and robot guidance.\n"
        entry += "Use the controls below to start and stop the camera, and manage sessions.\n"
        entry += "Happy detecting!\n"
        entry += "=" * 60 + "\n\n"
        
        # Add to history
        self.detection_history.append(entry)
        
        # Update text widget
        self.history_text.configure(state='normal')
        self.history_text.insert(tk.END, entry)
        self.history_text.configure(state='disabled')
        
        # Auto-scroll to bottom if enabled
        if self.history_autoscroll_var.get():
            self.history_text.see(tk.END)

    def add_demo_detection_events(self):
        """Add some demo detection events for immediate visibility"""
        # Add a demo detection event
        self.add_to_detection_history({
            "reading_materials": [{"box": [100, 100, 200, 200], "confidence": 0.85, "is_centered": True}],
            "faces": [{"box": [150, 150, 100, 100], "face_id": 1}],
            "robot_guidance": {"robot_command": "MOVE", "movement_magnitude": 100},
            "positioning": {"frame_width": 640, "frame_height": 480, "img_center_x": 320, "img_center_y": 240}
        })


def main():
    """Main entry point for GUI application"""
    print("Starting Camera Tool GUI...")
    
    # Create Tkinter root
    root = tk.Tk()
    
    try:
        # Create and run GUI
        app = CameraToolGUI(root)
        root.mainloop()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.exception(f"Error in GUI application: {e}")
        print(f"Error: {e}")
    finally:
        # Cleanup
        if hasattr(app, 'camera_tool'):
            app.camera_tool.process_command("stop_camera", {})



    def safe_widget_update(self, widget_update_func):
        """Safely update widget with error handling"""
        try:
            widget_update_func()
        except Exception as e:
            print(f"Widget update error: {e}")
            logger.exception(f"Widget update failed: {e}")

if __name__ == "__main__":
    main() 