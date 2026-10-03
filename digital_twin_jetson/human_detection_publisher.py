#!/usr/bin/env python3
"""
Human Detection Publisher Node (ROS 2 Humble)
==============================================
Mengintegrasikan sistem deteksi YOLOv11 + Intel RealSense
dengan ROS 2 untuk Social-Dynamic System control.

Fungsi:
  - Menjalankan deteksi manusia menggunakan YOLOv11 nano
  - Mengukur jarak menggunakan Intel RealSense depth camera
  - Publish data deteksi ke ROS 2 topic /human_detections

Output topic: /human_detections (custom message)
  - array of humans: [id, x_pixel, y_pixel, distance_m, bbox]

Author: Brone Social Nav Team
Version: 1.0
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import time


class HumanDetectionPublisher(Node):
    def __init__(self):
        super().__init__('human_detection_publisher')
        
        # Publisher
        self.pub_detections = self.create_publisher(String, '/human_detections', 10)
        
        # Load YOLOv11 model
        self.get_logger().info("Loading YOLOv11 model...")
        self.model = YOLO("yolo11n.pt")
        
        # Configure Intel RealSense
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        # Start streaming
        self.get_logger().info("Starting RealSense camera...")
        self.profile = self.pipeline.start(self.config)
        
        # Align depth to color
        self.align = rs.align(rs.stream.color)
        
        # Camera intrinsics (untuk konversi pixel ke world coordinates)
        color_stream = self.profile.get_stream(rs.stream.color)
        self.intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        
        # Timer untuk deteksi (10 Hz)
        self.create_timer(0.1, self.detection_callback)
        
        # Tracking ID counter
        self.next_id = 1
        self.tracked_humans = {}  # {id: (cx, cy, last_seen_time)}
        
        # Window untuk visualisasi (optional)
        self.show_visualization = True
        
        self.get_logger().info("✅ Human Detection Publisher initialized")
        self.get_logger().info(f"   Camera: {self.intrinsics.width}x{self.intrinsics.height}")
        self.get_logger().info(f"   FOV: {self.intrinsics.fx:.1f}px focal length")
    
    def pixel_to_camera_frame(self, cx, cy, depth_m):
        """
        Konversi koordinat pixel + depth ke camera frame (x, y, z)
        x: kanan (+), y: bawah (+), z: depan (+)
        """
        x = (cx - self.intrinsics.ppx) / self.intrinsics.fx * depth_m
        y = (cy - self.intrinsics.ppy) / self.intrinsics.fy * depth_m
        z = depth_m
        return x, y, z
    
    def camera_to_robot_frame(self, cam_x, cam_y, cam_z):
        """
        Transformasi dari camera frame ke robot frame
        Asumsi kamera mounted di depan robot:
          - Robot X: depan (+forward)
          - Robot Y: kiri (+left)
          - Robot Z: atas (+up)
        
        Camera frame:
          - Camera X: kanan
          - Camera Y: bawah
          - Camera Z: depan
        
        Mapping:
          robot_x = +cam_z (depan kamera = depan robot)
          robot_y = -cam_x (kanan kamera = kiri robot)
          robot_z = -cam_y (bawah kamera = atas robot)
        """
        robot_x = cam_z
        robot_y = -cam_x
        robot_z = -cam_y
        return robot_x, robot_y, robot_z
    
    def match_detection_to_track(self, cx, cy):
        """
        Simple tracking: cari human terdekat dalam radius 50 pixel
        """
        min_dist = 50  # pixels
        matched_id = None
        
        current_time = time.time()
        
        # Hapus track yang sudah lama tidak terlihat (>2 detik)
        to_remove = []
        for hid, (tx, ty, t_seen) in self.tracked_humans.items():
            if current_time - t_seen > 2.0:
                to_remove.append(hid)
        for hid in to_remove:
            del self.tracked_humans[hid]
        
        # Cari match terdekat
        for hid, (tx, ty, _) in self.tracked_humans.items():
            dist = np.hypot(cx - tx, cy - ty)
            if dist < min_dist:
                min_dist = dist
                matched_id = hid
        
        # Jika tidak ada match, buat ID baru
        if matched_id is None:
            matched_id = self.next_id
            self.next_id += 1
        
        # Update track
        self.tracked_humans[matched_id] = (cx, cy, current_time)
        
        return matched_id
    
    def detection_callback(self):
        """Main detection loop - dipanggil setiap 100ms (10 Hz)"""
        try:
            # Wait for frames
            frames = self.pipeline.wait_for_frames(timeout_ms=100)
            
            # Align frames
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return
            
            # Convert to numpy
            frame = np.asanyarray(color_frame.get_data())
            
            # Run YOLO inference - filter for humans only (class 0)
            results = self.model(frame, classes=[0], verbose=False)
            
            # Extract detections
            boxes = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
            confidences = results[0].boxes.conf.cpu().numpy()
            
            detections = []
            
            for i, (box, conf) in enumerate(zip(boxes, confidences)):
                x1, y1, x2, y2 = map(int, box[:4])
                
                # Center point
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                # Get distance at center
                distance = depth_frame.get_distance(cx, cy)
                
                # Skip if distance invalid
                if distance <= 0.1 or distance > 10.0:  # range 0.1m - 10m
                    continue
                
                # Match to existing track or create new ID
                human_id = self.match_detection_to_track(cx, cy)
                
                # Convert to camera frame
                cam_x, cam_y, cam_z = self.pixel_to_camera_frame(cx, cy, distance)
                
                # Convert to robot frame
                robot_x, robot_y, robot_z = self.camera_to_robot_frame(cam_x, cam_y, cam_z)
                
                detection = {
                    'id': human_id,
                    'pixel_x': cx,
                    'pixel_y': cy,
                    'distance': round(distance, 3),
                    'bbox': [x1, y1, x2, y2],
                    'confidence': round(float(conf), 3),
                    'position': {
                        'x': round(robot_x, 3),  # meters, forward
                        'y': round(robot_y, 3),  # meters, left
                        'z': round(robot_z, 3)   # meters, up
                    }
                }
                detections.append(detection)
            
            # Publish detections
            msg = String()
            msg.data = json.dumps({
                'timestamp': self.get_clock().now().nanoseconds / 1e9,
                'num_humans': len(detections),
                'detections': detections
            })
            self.pub_detections.publish(msg)
            
            # Log
            if len(detections) > 0:
                self.get_logger().info(
                    f"Detected {len(detections)} humans | "
                    + ", ".join([
                        f"ID{d['id']}:({d['position']['x']:.2f},{d['position']['y']:.2f})@{d['distance']:.2f}m"
                        for d in detections
                    ])
                )
            
            # Visualization (optional)
            if self.show_visualization:
                annotated_frame = results[0].plot()
                for detection in detections:
                    x1, y1, x2, y2 = detection['bbox']
                    cv2.putText(
                        annotated_frame,
                        f"ID{detection['id']} {detection['distance']:.2f}m",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )
                    cv2.putText(
                        annotated_frame,
                        f"({detection['position']['x']:.2f}, {detection['position']['y']:.2f})",
                        (x1, max(y1 - 30, 40)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 0),
                        1
                    )
                
                cv2.imshow("Human Detection - ROS 2", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.show_visualization = False
                    cv2.destroyAllWindows()
        
        except Exception as e:
            self.get_logger().error(f"Detection error: {e}")
    
    def shutdown(self):
        """Clean shutdown"""
        self.get_logger().info("Stopping detection...")
        self.pipeline.stop()
        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = HumanDetectionPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
