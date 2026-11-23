import cv2
import numpy as np

print("Testing camera hardware...")

# Try different camera indices
for i in range(3):
    print(f"\nTesting camera index {i}...")
    cap = cv2.VideoCapture(i)
    
    if cap.isOpened():
        print(f"Camera {i} opened successfully!")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print(f"Frame captured successfully! Shape: {frame.shape}")
            print(f"Camera resolution: {int(cap.get(3))}x{int(cap.get(4))}")
            
            # Save test image
            cv2.imwrite(f"test_camera_{i}.jpg", frame)
            print(f"Test image saved as test_camera_{i}.jpg")
        else:
            print(f"Failed to read frame from camera {i}")
        
        cap.release()
    else:
        print(f"Failed to open camera {i}")

print("\nCamera test completed!")
