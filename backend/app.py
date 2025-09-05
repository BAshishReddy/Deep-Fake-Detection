import os 
import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
from tensorflow.keras.models import load_model  # type: ignore

app = Flask(__name__)
CORS(app)  # Enable CORS

# Load your saved model
model = load_model('mydeepfakemodel.h5')
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])  # Re-compile the model



# Data augmentation function (mirroring training)
def augment_frame(frame):
    """Apply random augmentations to a frame."""
    if np.random.rand() > 0.5:
        frame = cv2.flip(frame, 1)  # Random horizontal flip
    angle = np.random.uniform(-15, 15)  # Random rotation angle
    center = (frame.shape[1] // 2, frame.shape[0] // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    frame = cv2.warpAffine(frame, matrix, (frame.shape[1], frame.shape[0]))
    return frame

# Preprocessing function for the uploaded video with augmentation
def preprocess_video(video_path, sequence_length=20, img_height=128, img_width=128):
    """Extract and preprocess frames from the video file."""
    cap = cv2.VideoCapture(video_path)
    frames = []

    while len(frames) < sequence_length:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (img_width, img_height))  # Resize frame
        frame = augment_frame(frame)  # Apply augmentation
        frames.append(frame)
    
    cap.release()
    
    # Pad with zeros if fewer frames than sequence length
    while len(frames) < sequence_length:
        frames.append(np.zeros((img_height, img_width, 3), dtype=np.uint8))

    frames = np.array(frames)
    return frames

@app.route('/predict', methods=['POST'])
@app.route('/predict', methods=['POST'])
def predict():
    """Handle video file upload and perform prediction."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'})

    video_file = request.files['file']
    
    # Debugging output
    print("Received file:", video_file.filename)
    print("File type:", video_file.content_type)
    
    if video_file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Save the uploaded video to a temporary file
    video_path = os.path.join('uploads', video_file.filename)
    video_file.save(video_path)
    
    # Preprocess the video and perform prediction
    try:
        video_data = preprocess_video(video_path)  # Preprocess the video
        video_data = np.expand_dims(video_data, axis=0)  # Add batch dimension

        # Perform prediction
        prediction = model.predict(video_data)
        print("Raw prediction output:", prediction)  # Output raw predictions for debugging

        threshold = 0.6
        label = 1 if prediction[0][1] > threshold else 0

        prediction_values = prediction[0]  # Get raw prediction values

        result = 'FAKE' if label == 1 else 'REAL'
    except Exception as e:
        result = f'Error: {str(e)}'
        prediction_values = None
    
    # Clean up: Delete the video after prediction
    os.remove(video_path)
    
    return jsonify({'prediction': result , 'prediction_values': prediction_values.tolist() if prediction_values is not None else None})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)