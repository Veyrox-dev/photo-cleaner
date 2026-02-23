from mtcnn import MTCNN
import cv2

detector = MTCNN()
img = cv2.imread('test_data_system/5k/test_img_00001.jpg')
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

faces = detector.detect_faces(rgb)
print(f'✅ MTCNN 0.1.1 - Faces found: {len(faces)}')
for i, f in enumerate(faces):
    print(f'  Face {i+1}: confidence={f["confidence"]:.2f}, box={f["box"]}')
