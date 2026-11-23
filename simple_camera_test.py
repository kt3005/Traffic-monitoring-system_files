import cv2
import time

print("=== SIMPLE CAMERA TEST ===")
print("Testing camera access without Flask...")

# Test all possible camera indices
for camera_index in range(5):
    print(f"\n--- Testing Camera Index {camera_index} ---")
    
    try:
        cap = cv2.VideoCapture(camera_index)
        
        if cap.isOpened():
            print(f"✓ Camera {camera_index} opened successfully")
            
            # Try to get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps}")
            
            # Try to read multiple frames
            success_count = 0
            for i in range(5):
                ret, frame = cap.read()
                if ret:
                    success_count += 1
                    if i == 0:
                        print(f"  First frame shape: {frame.shape}")
                        # Save first frame as test
                        cv2.imwrite(f"camera_test_{camera_index}_frame.jpg", frame)
                        print(f"  Test image saved: camera_test_{camera_index}_frame.jpg")
                else:
                    print(f"  Failed to read frame {i+1}")
                    break
            
            print(f"  Successfully read {success_count}/5 frames")
            
            cap.release()
            
            if success_count > 0:
                print(f"✓ Camera {camera_index} is WORKING!")
            else:
                print(f"✗ Camera {camera_index} opened but failed to read frames")
                
        else:
            print(f"✗ Failed to open camera {camera_index}")
            
    except Exception as e:
        print(f"✗ Exception with camera {camera_index}: {e}")

print("\n=== TEST COMPLETE ===")
print("Check the saved test images to verify camera is working.")
print("\nIf no cameras worked, possible issues:")
print("1. Camera is being used by another application")
print("2. Windows camera permissions are blocked")
print("3. No camera hardware connected")
print("4. Camera drivers not installed")

input("\nPress Enter to exit...")
