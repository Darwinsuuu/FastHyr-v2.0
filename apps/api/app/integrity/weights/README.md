# Face models (ASMT-002)

The worker's same-face check runs these two models from the OpenCV Model Zoo locally, through
OpenCV's `FaceDetectorYN` and `FaceRecognizerSF` (`app/integrity/faces.py`). Nothing is sent
anywhere, and no embedding or frame outlives the job (ADR-016).

| File | Model | Source | Licence | SHA-256 |
|---|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | YuNet face detector (2023-03) | `opencv/opencv_zoo` `models/face_detection_yunet` | MIT | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| `face_recognition_sface_2021dec_int8.onnx` | SFace face recognition, int8 quantised (2021-12) | `opencv/opencv_zoo` `models/face_recognition_sface` | Apache-2.0 | `2b0e941e6f16cc048c20aee0c8e31f569118f65d702914540f7bfdc14048d78a` |

To update one, download the new file from the OpenCV Model Zoo, check its licence, replace the
file, update the table and `FACE_MODEL` in `app/integrity/faces.py` (it is recorded with every
face flag), and run the face tests (`tests/unit/test_integrity_faces.py`).
